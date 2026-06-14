"""OVS network orchestration utils.

This part includes utilities, logging setup, and schema definitions.
Provides a logger provider function for use in other modules.
"""

from __future__ import annotations

import asyncio
import errno
import hashlib
import ipaddress
import json
import logging
import os
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Any, TypedDict, TypeVar

from tinydb import Query, TinyDB
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage

# Constants
DB_JSON_PATH = Path("/tmp/db.json")  # noqa: S108
DOCKER_SOCKET = Path("/var/run/docker.sock")
USE_LINUX_BRIDGE = os.environ.get("USE_LINUX_BRIDGE", "false") in ("true", "1")
EVENT_LOCK = asyncio.Lock()
T = TypeVar("T")

# Runtime-config (Bug 1)
ROOT_CONFIG_PATH = Path("/root/config.json")
RUNTIME_CONFIG_PATH = Path("/tmp/runtime-config.json")  # noqa: S108

# Shared flush trigger (Bug 1 + Bug 2)
QUIET_SECONDS = 60.0
_state: dict[str, Any] = {
    "config_dirty": False,
    "db_dirty": False,
    "last_mutation_ts": 0.0,
    "last_external_mtime": 0.0,
    "last_success_ts": 0.0,
}


def atomic_write_json(path: Path, data: object) -> None:
    """Atomically write JSON to `path` via tempfile + os.replace.

    Guards against torn writes if the orchestrator crashes mid-write or if an
    external reader opens the file concurrently.

    :param path: Destination file path.
    :type path: Path
    :param data: JSON-serialisable payload.
    :type data: object
    :raises Exception: Re-raises any exception from the write/replace operation after cleaning up the temp file.
    """
    parent = path.parent
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp)
            fp.flush()
            os.fsync(fp.fileno())
        try:
            Path(tmp_name).replace(path)
        except OSError as exc:
            if exc.errno != errno.EBUSY:
                raise
            # Docker bind-mounted file: os.rename can't swap the inode.
            # Fall back to in-place overwrite of the same inode.
            content = Path(tmp_name).read_text(encoding="utf-8")
            path.write_text(content, encoding="utf-8")
            Path(tmp_name).unlink(missing_ok=True)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def deep_merge(dst: dict[str, Any], src: Mapping[str, Any]) -> dict[str, Any]:
    """In-place deep-merge `src` into `dst`. Returns `dst` for chaining.

    Rules: scalars overwrite, dicts merge recursively, lists overwrite
    wholesale (no element-level merging). Matches the existing config shape
    where `container[name]` is a list of interface dicts that external editors
    replace wholesale.

    :param dst: Destination dict (mutated in place).
    :param src: Source mapping; values from here win on overlap.
    :return: `dst`.
    """
    for key, value in src.items():
        if key in dst and isinstance(dst[key], dict) and isinstance(value, Mapping):
            deep_merge(dst[key], value)
        else:
            dst[key] = value
    return dst


def mark_config_dirty() -> None:
    """Signal that the in-memory config has diverged from `/root/config.json`."""
    _state["config_dirty"] = True
    _state["last_mutation_ts"] = time.monotonic()


def mark_db_dirty() -> None:
    """Signal that TinyDB has uncommitted writes."""
    _state["db_dirty"] = True
    _state["last_mutation_ts"] = time.monotonic()


def mark_tick_success() -> None:
    """Signal a clean reconcile tick.

    Called by `main()` at the end of each pass. Used by `runner.py`'s
    supervisor: if a task crash is observed AND a successful tick happened
    since the previous crash, the supervisor resets `_crash_count` (we
    tolerate intermittent failures the loop recovers from).
    """
    _state["last_success_ts"] = time.monotonic()


def is_config_dirty() -> bool:
    """Whether `/tmp/runtime-config.json` has unpersisted changes vs `/root/config.json`.

    :return: True if the in-memory config has diverged from disk, False otherwise.
    :rtype: bool
    """
    return bool(_state["config_dirty"])


def is_db_dirty() -> bool:
    """Whether TinyDB has uncommitted writes.

    :return: True if TinyDB has uncommitted writes, False otherwise.
    :rtype: bool
    """
    return bool(_state["db_dirty"])


def clear_config_dirty() -> None:
    """Mark the config flush as complete."""
    _state["config_dirty"] = False


def clear_db_dirty() -> None:
    """Mark the db commit as complete."""
    _state["db_dirty"] = False


def get_last_success_ts() -> float:
    """Most recent successful-tick timestamp (0.0 if no tick has succeeded yet).

    :return: Monotonic timestamp of the last successful reconcile tick.
    :rtype: float
    """
    return float(_state["last_success_ts"])


_config_cache: dict[str, object] | None = None


def _normalize_veth_pairs(config: dict) -> None:
    """Convert legacy dict-form veth_pairs to list form in-place.

    Old form: ``{"eth3": {"on": "bridgeA", "map": "100:"}}``
    New form: ``[{"id": "eth3", "on": "bridgeA", "map": "100:"}]``

    No-op when veth_pairs is already a list or absent.

    :param config: Config dict to normalize (mutated in place).
    :type config: dict
    """
    vp = config.get("veth_pairs")
    if isinstance(vp, dict):
        config["veth_pairs"] = [{"id": k, **v} for k, v in vp.items()]


def bootstrap_runtime_config() -> dict[str, object]:
    """Seed `_config_cache` from disk on orchestrator startup.

    If `/tmp/runtime-config.json` exists, load it (preserves API mutations
    across a supervisord-driven process restart inside the same container).
    Otherwise copy `/root/config.json` → `/tmp/runtime-config.json` and load.
    Records `last_external_mtime`.

    :return: The loaded in-memory config dict.
    :rtype: dict[str, object]
    """
    global _config_cache  # noqa: PLW0603
    if RUNTIME_CONFIG_PATH.exists():
        _LOGGER.info("Loading runtime config from %s", RUNTIME_CONFIG_PATH)
        with RUNTIME_CONFIG_PATH.open(encoding="utf-8") as fp:
            _config_cache = json.load(fp)
        _normalize_veth_pairs(_config_cache)
    else:
        _LOGGER.info("Seeding %s from %s", RUNTIME_CONFIG_PATH, ROOT_CONFIG_PATH)
        with ROOT_CONFIG_PATH.open(encoding="utf-8") as fp:
            _config_cache = json.load(fp)
        _normalize_veth_pairs(_config_cache)
        atomic_write_json(RUNTIME_CONFIG_PATH, _config_cache)
    _state["last_external_mtime"] = ROOT_CONFIG_PATH.stat().st_mtime
    return _config_cache


def save_runtime_config() -> None:
    """Atomically write the in-memory config dict to `/tmp/runtime-config.json`.

    Called from API routers after every successful mutation.
    """
    if _config_cache is None:
        return
    atomic_write_json(RUNTIME_CONFIG_PATH, _config_cache)


def ingress_external_config() -> bool:
    """Pull external edits from `/root/config.json` into the in-memory config.

    Called at the top of every reconcile tick under `EVENT_LOCK`. Mtime-gated:
    re-reads `/root/config.json` only when its mtime has advanced past the last
    observed value. External values win on overlapping keys (deep-merge).

    Returns `True` if a merge occurred.

    :return: True if an external merge was performed, False otherwise.
    :rtype: bool
    """
    if _config_cache is None:
        return False
    try:
        current_mtime = ROOT_CONFIG_PATH.stat().st_mtime
    except FileNotFoundError:
        _LOGGER.warning("%s missing; skipping ingress", ROOT_CONFIG_PATH)
        return False

    if current_mtime <= _state["last_external_mtime"]:
        return False

    try:
        with ROOT_CONFIG_PATH.open(encoding="utf-8") as fp:
            external = json.load(fp)
    except json.JSONDecodeError:
        _LOGGER.exception(
            "Partial / invalid JSON in %s; will retry next tick", ROOT_CONFIG_PATH
        )
        return False

    _normalize_veth_pairs(external)
    _LOGGER.info("External config mtime advanced; merging")
    deep_merge(_config_cache, external)
    atomic_write_json(RUNTIME_CONFIG_PATH, _config_cache)
    _state["last_external_mtime"] = current_mtime
    # We just absorbed external state; clear config_dirty so we don't bounce it
    # back on the next quiet-window flush.
    _state["config_dirty"] = False
    return True


def flush_runtime_config_to_root() -> None:
    """Atomically write the in-memory config dict to `/root/config.json`.

    Refreshes `last_external_mtime` from the resulting file's mtime so the next
    ingress check doesn't treat our own write as an external edit.
    """
    if _config_cache is None:
        return
    atomic_write_json(ROOT_CONFIG_PATH, _config_cache)
    _state["last_external_mtime"] = ROOT_CONFIG_PATH.stat().st_mtime
    _LOGGER.info("Flushed runtime config to %s", ROOT_CONFIG_PATH)


def maybe_flush_state() -> None:
    """End-of-tick flush. Fires only after a quiet window.

    Called from `main()` at the bottom of each reconcile tick, under
    `EVENT_LOCK`. If nothing has been mutated, returns immediately. If the
    quiet window hasn't elapsed since the last mutation, returns immediately.
    Otherwise flushes whichever flags are set.
    """
    if _state["last_mutation_ts"] == 0.0:
        return
    if (time.monotonic() - _state["last_mutation_ts"]) < QUIET_SECONDS:
        return
    if is_config_dirty():
        flush_runtime_config_to_root()
        clear_config_dirty()
    if is_db_dirty():
        commit_db()
        clear_db_dirty()


class AtomicJSONStorage(JSONStorage):
    """JSONStorage that writes via tempfile + os.replace to avoid torn files.

    TinyDB's default JSONStorage writes the file in place. On a crash mid-write
    the file can be left empty or partially written; on next open TinyDB sees
    invalid JSON. AtomicJSONStorage writes a sibling tempfile then `os.replace`s
    it over the target — atomic at the directory level on POSIX.
    """

    def write(self, data: dict[str, object]) -> None:  # type: ignore[override]
        """Write `data` atomically via tempfile + os.replace.

        :param data: TinyDB document store to persist.
        :type data: dict[str, object]
        """
        path = Path(self._handle.name)
        atomic_write_json(path, data)


_db: TinyDB | None = None


def get_tinydb() -> TinyDB:
    """Return the process-wide TinyDB singleton (lazy-initialised).

    Uses CachingMiddleware over AtomicJSONStorage so writes accumulate in memory
    until `commit_db()` flushes them. This is the "explicit commit" boundary —
    callers mutate freely and the reconcile loop / shutdown decides when to
    persist.

    :return: The process-wide TinyDB instance.
    :rtype: TinyDB
    """
    global _db  # noqa: PLW0603
    if _db is None:
        _db = TinyDB(str(DB_JSON_PATH), storage=CachingMiddleware(AtomicJSONStorage))
    return _db


def commit_db() -> None:
    """Flush the TinyDB CachingMiddleware buffer to disk."""
    if _db is not None:
        _db.storage.flush()


def close_db() -> None:
    """Close the TinyDB singleton (flushes on close). Used at shutdown."""
    global _db  # noqa: PLW0603
    if _db is not None:
        _db.close()
        _db = None


def get_meta(key: str, default: object = None) -> object:
    """Read a scalar from the `meta` table. Returns `default` if missing.

    :param key: The metadata key to look up.
    :type key: str
    :param default: Value to return when the key is absent.
    :type default: object
    :return: The stored value for `key`, or `default` if not found.
    :rtype: object
    """
    row = get_tinydb().table("meta").get(Query().key == key)
    return row["value"] if row else default


def set_meta(key: str, value: object) -> None:
    """Upsert a scalar into the `meta` table. Diff-aware — only marks dirty on change.

    :param key: The metadata key to set.
    :type key: str
    :param value: The value to store for `key`.
    :type value: object
    """
    table = get_tinydb().table("meta")
    existing = table.get(Query().key == key)
    if existing is not None and existing.get("value") == value:
        return  # no-op, no dirty
    table.upsert({"key": key, "value": value}, Query().key == key)
    mark_db_dirty()


def get_bridge(name: str) -> dict[str, object] | None:
    """Return the `bridges` row for `name`, or `None`.

    :param name: The bridge name to look up.
    :type name: str
    :return: The TinyDB row dict for the bridge, or None if not found.
    :rtype: dict[str, object] | None
    """
    return get_tinydb().table("bridges").get(Query().name == name)


def upsert_bridge(name: str, **fields: object) -> None:
    """Upsert per-bridge fields (iprange, ip6range, etc.). Diff-aware.

    Does not touch `hosts_v4` / `hosts_v6` — use `set_bridge_host` /
    `clear_bridge_host` for those.

    :param name: The bridge name to upsert.
    :type name: str
    :param fields: Keyword arguments for bridge fields to set (e.g. iprange, ip6range).
    :type fields: dict[str, object]
    """
    table = get_tinydb().table("bridges")
    existing = table.get(Query().name == name) or {}
    merged = {
        "name": name,
        **{k: v for k, v in existing.items() if k != "name"},
        **fields,
    }
    if merged == existing:
        return
    table.upsert(merged, Query().name == name)
    mark_db_dirty()


def get_bridge_hosts(name: str, family: str = "ip") -> dict[str, str]:
    """Return the `hosts_v4` (or `hosts_v6`) sub-map for the bridge.

    :param name: The bridge name to look up.
    :type name: str
    :param family: `"ip"` or `"ip6"`. Empty dict if the bridge or sub-map is absent.
    :type family: str
    :return: Mapping of container name to allocated IP address for the given family.
    :rtype: dict[str, str]
    """
    field = "hosts_v4" if family == "ip" else "hosts_v6"
    row = get_bridge(name)
    return (row or {}).get(field, {})


def set_bridge_host(name: str, container: str, family: str, ipaddr: str) -> None:
    """Assign / overwrite a host entry. Diff-aware.

    :param name: Bridge name.
    :param container: Container (or bridge) name being assigned the IP.
    :param family: `"ip"` or `"ip6"`.
    :param ipaddr: IP in `addr/mask` form.
    """
    field = "hosts_v4" if family == "ip" else "hosts_v6"
    table = get_tinydb().table("bridges")
    existing = table.get(Query().name == name) or {"name": name}
    hosts = dict(existing.get(field, {}))
    if hosts.get(container) == ipaddr:
        return
    hosts[container] = ipaddr
    new_row = {**existing, field: hosts}
    table.upsert(new_row, Query().name == name)
    mark_db_dirty()


def clear_bridge_host(name: str, container: str, family: str) -> None:
    """Remove a host entry. Diff-aware (no-op if absent).

    :param name: The bridge name.
    :type name: str
    :param container: The container name whose host entry should be removed.
    :type container: str
    :param family: `"ip"` or `"ip6"`.
    :type family: str
    """
    field = "hosts_v4" if family == "ip" else "hosts_v6"
    table = get_tinydb().table("bridges")
    existing = table.get(Query().name == name)
    if not existing:
        return
    hosts = dict(existing.get(field, {}))
    if container not in hosts:
        return
    hosts.pop(container)
    new_row = {**existing, field: hosts}
    table.upsert(new_row, Query().name == name)
    mark_db_dirty()


def clear_bridge_hosts(name: str, family: str) -> None:
    """Wipe the entire hosts sub-map for a family. Used when iprange changes.

    :param name: The bridge name.
    :type name: str
    :param family: `"ip"` or `"ip6"`.
    :type family: str
    """
    field = "hosts_v4" if family == "ip" else "hosts_v6"
    table = get_tinydb().table("bridges")
    existing = table.get(Query().name == name)
    if not existing or not existing.get(field):
        return
    new_row = {**existing, field: {}}
    table.upsert(new_row, Query().name == name)
    mark_db_dirty()


# TypedDict schemas for network configurations
class IfaceInfoDict(TypedDict, total=False):
    """Schema for OVS/Linux Bridge parent interface details."""

    iface: str  # Optional, parent interface OVS speaks to
    native: str  # Optional, native VLAN for untagged packets
    trunk: str  # Optional, Comma separated VLAN ids
    vlan: str  # Optional, access VLAN


class BridgeInfoDict(TypedDict, total=False):
    """Schema for OVS/Linux Bridge details."""

    parents: list[IfaceInfoDict]
    iprange: str  # Optional, subnet with prefix
    ip6range: str  # Optional, subnet with prefix
    ipaddress: str  # Optional, IPv4 address
    ip6address: str  # Optional, IPv6 address


class ContainerInfoDict(TypedDict, total=False):
    """Schema for Container Interface Bridge details."""

    iface: str  # Interface name inside of container.
    bridge: str  # Bridge name interface needs to be part of
    vlan: str  # Optional, VLAN ID interface should be part of
    trunk: str  # Optional, Comma separated VLAN ids
    ipaddress: str  # Optional, IPv4 address
    ip6address: str  # Optional, IPv6 address
    gateway: str  # Optional, IPv4 gateway address
    gateway6: str  # Optional, IPv6 gateway address
    macaddress: str  # Optional, MAC address for the interface


class VethPairItemDict(TypedDict):
    """Schema for a veth pair list entry — required fields."""

    id: str  # ≤8-char prefix; names v0_<id> / v1_<id> interfaces
    on: str  # Bridge to attach v0_ end


class VethPairItemOptDict(VethPairItemDict, total=False):
    """Schema for a veth pair list entry — optional fields."""

    map: str  # VLAN translation e.g. "100:200"
    trunk: str  # "yes" or "no"


# Publicly accessible function to provide logger
def get_logger(name: str = __name__) -> logging.Logger:
    """Return a logger configured for the provided module or function.

    :param name: The name of the logger (usually module or function name).
    :type name: str
    :return: A configured logger instance.
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(
        logging.DEBUG if os.environ.get("DEBUG", "no") == "yes" else logging.INFO
    )

    # Stream handler for output
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if logger.level == logging.DEBUG else logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(funcName)s:: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


_LOGGER = get_logger("utils")


def get_config() -> dict[str, object]:
    """Return the live in-memory config dict.

    The dict is seeded by `bootstrap_runtime_config()` on orchestrator startup
    and mutated in place by API routers + the reconcile loop's ingress merge.
    Identity is stable across calls so callers can hold references safely.

    :return: The live in-memory config dict.
    :rtype: dict[str, object]
    :raises RuntimeError: If called before `bootstrap_runtime_config()`.
    """
    if _config_cache is None:
        msg = "get_config() called before bootstrap_runtime_config()"
        raise RuntimeError(msg)
    return _config_cache


def hash_string(string: str) -> str:
    """Hashes a string using the SHA-256 algorithm.

    :param string: input string
    :type string: str
    :return: first 8 bits as an 8-bit string.
    :rtype: str
    """
    return hashlib.sha256(string.encode()).hexdigest()[:8]


def check_container_exists(container_name: str) -> bool:
    """Check if the container exists.

    :param container_name: Name of the container.
    :type container_name: str
    :return: True if the container exists, False otherwise.
    :rtype: bool
    """
    check = run_command(f"docker ps -f name={container_name}$ -q", check=False)
    exists = bool(check.stdout.strip())
    if not exists:
        _LOGGER.debug("Container %s does not exist!", container_name)
    else:
        _LOGGER.debug("Container ID: %s", check.stdout.strip())
    return exists


def run_command(command: str, check: bool = True) -> CompletedProcess[str]:
    """Run a command using subprocess and capture the output.

    :param command: The command to run.
    :type command: str
    :param check: Flag to raise an exception on command failure.
    :type check: bool
    :return: The captured output of the command as a string.
    :rtype: CompletedProcess[str]
    :raises CalledProcessError: If the command execution fails.
    """
    try:
        return run(command.split(), check=check, capture_output=True, text=True)
    except CalledProcessError as exc:
        _LOGGER.exception("Subprocess error:\nCommand failed: %s", exc.cmd)
        stderr_output = exc.stderr or None
        _LOGGER.exception("Command stderr output:\n%s", stderr_output)
        raise


def get_usb_interface(usb_port: str) -> str:
    """Get the network interface associated with a given USB port.

    This function identifies the network interface corresponding to a
    specific USB port. It searches through `/sys/class/net` to find
    interfaces attached to the given USB bus.

    :param usb_port: The USB port identifier (e.g., "1-1").
    :type usb_port: str
    :return: The network interface associated with the USB port.
    :rtype: str
    :raises ValueError: If multiple or no interfaces are found for the specified USB port.
    """
    devs = run_command("ls -l /sys/class/net", check=False)

    usb_info = [dev for dev in devs.stdout.splitlines() if usb_port in dev]
    if len(usb_info) > 1:
        msg = f"Identified more than one interface for USB bus: {usb_port}"
        raise ValueError(msg)
    if not usb_info:
        err = f"No network interface found for USB port: {usb_port}"
        raise ValueError(err)

    # Assumption 8th section of split of each line shows the interface name.
    return usb_info[0].split()[8]


def auto_allocate_ip(bridge_name: str, container_name: str, family: str = "ip") -> str:
    """Automatically allocate an IP address from the bridge's IP range.

    :param bridge_name: Bridge to allocate IP from for the container.
    :param container_name: Container being assigned the IP.
    :param family: `"ip"` for IPv4 or `"ip6"` for IPv6.
    :raises IndexError: If no available IPs remain in the range.
    :return: Allocated IP with prefix mask.
    """
    bridge_row = get_bridge(bridge_name) or {}
    range_key = f"{family}range"
    ip_range = bridge_row.get(range_key, "/24")
    hosts = get_bridge_hosts(bridge_name, family)

    network_hosts = ipaddress.ip_network(str(ip_range)).hosts()
    _ = [next(network_hosts) for _ in range(5)]  # Skip first 5 addresses

    for host in network_hosts:
        ipaddr = f"{host}/{ip_range.split('/')[-1]}"
        if ipaddr not in hosts.values():
            _LOGGER.debug(
                "Automatic IP allocation (%s) to container: %s", ipaddr, container_name
            )
            set_bridge_host(bridge_name, container_name, family, ipaddr)
            return ipaddr

    msg = f"Failed to automatically allocate an IP to container: {container_name}"
    raise IndexError(msg)


def validate_bridge(bridge_name: str, info: BridgeInfoDict) -> bool:
    """Validate the bridge can be added.

    Fails if the bridge already exists AND one of its parent interfaces is
    already registered as a `bridge_iface` on that bridge.

    :param bridge_name: The bridge name to validate.
    :type bridge_name: str
    :param info: The bridge configuration dict to validate against.
    :type info: BridgeInfoDict
    :return: True if the bridge can be safely added, False otherwise.
    :rtype: bool
    """
    if get_bridge(bridge_name) is None:
        return True
    _LOGGER.debug("Bridge already exists: %s", bridge_name)
    for parent in info.get("parents", []):
        iface = parent.get("iface", "")
        if iface and has_bridge_iface(bridge_name, iface):
            _LOGGER.error("iface %s exists in bridge: %s", iface, bridge_name)
            return False
    return True


def validate_container(container_id: str, info: ContainerInfoDict) -> bool:
    """Validate the container interface can be added.

    Fails if the `(bridge, container, iface)` triple already exists.

    :param container_id: The container name to validate.
    :type container_id: str
    :param info: The container interface configuration dict.
    :type info: ContainerInfoDict
    :return: True if the interface can be added to the container, False otherwise.
    :rtype: bool
    """
    bridge = info["bridge"]
    iface = info["iface"]
    if has_container_iface(bridge, container_id, iface):
        _LOGGER.error("iface %s already exists for container: %s", iface, container_id)
        return False
    return True


def validate_veth_pair(veth_pair_id: str, info: dict[str, object]) -> bool:
    """Validate the VETH pair can be added.

    Fails if the prefix is over 8 characters or if the veth0 endpoint
    (`v0_<prefix>`) is already registered on the target bridge.

    :param veth_pair_id: The veth pair prefix identifier to validate.
    :type veth_pair_id: str
    :param info: The veth pair configuration dict (must contain `"on"` key for bridge).
    :type info: dict[str, object]
    :return: True if the veth pair can be created, False otherwise.
    :rtype: bool
    """
    prefix_length_limit = 8
    if len(veth_pair_id) > prefix_length_limit:
        _LOGGER.error("VETH prefix ID: %s is more than 8 chars", veth_pair_id)
        return False
    veth0 = f"v0_{veth_pair_id}"
    if has_bridge_iface(str(info["on"]), veth0):
        _LOGGER.error("iface %s exists in bridge: %s", veth_pair_id, info["on"])
        return False
    return True


def get_bridge_iface(bridge: str, iface: str) -> dict[str, object] | None:
    """Return the `bridge_ifaces` row for `(bridge, iface)`, or `None`.

    :param bridge: The bridge name.
    :type bridge: str
    :param iface: The interface name.
    :type iface: str
    :return: The TinyDB row dict for the bridge-iface pair, or None if not found.
    :rtype: dict[str, object] | None
    """
    return (
        get_tinydb()
        .table("bridge_ifaces")
        .get((Query().bridge == bridge) & (Query().iface == iface))
    )


def has_bridge_iface(bridge: str, iface: str) -> bool:
    """Whether a `bridge_ifaces` row exists for `(bridge, iface)`.

    :param bridge: The bridge name.
    :type bridge: str
    :param iface: The interface name.
    :type iface: str
    :return: True if the bridge-iface row exists, False otherwise.
    :rtype: bool
    """
    return get_bridge_iface(bridge, iface) is not None


def upsert_bridge_iface(bridge: str, iface: str, **fields: object) -> None:
    """Upsert `(bridge, iface)` VLAN settings (trunk / native / vlan). Diff-aware.

    :param bridge: The bridge name.
    :type bridge: str
    :param iface: The interface name.
    :type iface: str
    :param fields: Keyword arguments for VLAN fields to set (e.g. trunk, native, vlan).
    :type fields: dict[str, object]
    """
    table = get_tinydb().table("bridge_ifaces")
    existing = table.get((Query().bridge == bridge) & (Query().iface == iface)) or {}
    merged = {
        "bridge": bridge,
        "iface": iface,
        **{k: v for k, v in existing.items() if k not in ("bridge", "iface")},
        **fields,
    }
    if merged == existing:
        return
    table.upsert(merged, (Query().bridge == bridge) & (Query().iface == iface))
    mark_db_dirty()


def get_container_iface(
    bridge: str, container: str, iface: str
) -> dict[str, object] | None:
    """Return the `container_ifaces` row for the triple, or `None`.

    :param bridge: The bridge name.
    :type bridge: str
    :param container: The container name.
    :type container: str
    :param iface: The interface name.
    :type iface: str
    :return: The TinyDB row dict for the (bridge, container, iface) triple, or None.
    :rtype: dict[str, object] | None
    """
    q = Query()
    return (
        get_tinydb()
        .table("container_ifaces")
        .get((q.bridge == bridge) & (q.container == container) & (q.iface == iface))
    )


def has_container_iface(bridge: str, container: str, iface: str) -> bool:
    """Whether a `container_ifaces` row exists for the triple.

    :param bridge: The bridge name.
    :type bridge: str
    :param container: The container name.
    :type container: str
    :param iface: The interface name.
    :type iface: str
    :return: True if the (bridge, container, iface) row exists, False otherwise.
    :rtype: bool
    """
    return get_container_iface(bridge, container, iface) is not None


def upsert_container_iface(
    bridge: str, container: str, iface: str, **fields: object
) -> None:
    """Upsert per-iface settings for a container interface. Diff-aware.

    :param bridge: The bridge name.
    :type bridge: str
    :param container: The container name.
    :type container: str
    :param iface: The interface name.
    :type iface: str
    :param fields: Keyword arguments for interface fields to set (e.g. vlan_mode).
    :type fields: dict[str, object]
    """
    q = Query()
    table = get_tinydb().table("container_ifaces")
    cond = (q.bridge == bridge) & (q.container == container) & (q.iface == iface)
    existing = table.get(cond) or {}
    merged = {
        "bridge": bridge,
        "container": container,
        "iface": iface,
        **{
            k: v
            for k, v in existing.items()
            if k not in ("bridge", "container", "iface")
        },
        **fields,
    }
    if merged == existing:
        return
    table.upsert(merged, cond)
    mark_db_dirty()


def get_all_container_ifaces() -> list[dict[str, object]]:
    """Return all rows from the `container_ifaces` table.

    :return: All tracked (bridge, container, iface) rows.
    :rtype: list[dict[str, object]]
    """
    return get_tinydb().table("container_ifaces").all()


def clear_container_iface(bridge: str, container: str, iface: str) -> None:
    """Remove the `container_ifaces` row for the triple. No-op if absent.

    :param bridge: The bridge name.
    :type bridge: str
    :param container: The container name.
    :type container: str
    :param iface: The interface name.
    :type iface: str
    """
    q = Query()
    table = get_tinydb().table("container_ifaces")
    cond = (q.bridge == bridge) & (q.container == container) & (q.iface == iface)
    removed = table.remove(cond)
    if removed:
        mark_db_dirty()


def get_all_veth_ifaces() -> list[dict[str, object]]:
    """Return all v0_-prefixed rows from `bridge_ifaces`.

    Returns one row per veth pair. Callers that delete pairs must use
    remove_veth_pair to clean up both v0_ and v1_ ends.

    :return: All tracked veth pair endpoint rows (v0_ prefix only).
    :rtype: list[dict[str, object]]
    """
    return get_tinydb().table("bridge_ifaces").search(Query().iface.matches(r"^v0_"))


def clear_bridge_iface(bridge: str, iface: str) -> None:
    """Remove the `bridge_ifaces` row for `(bridge, iface)`. No-op if absent.

    :param bridge: The bridge name.
    :type bridge: str
    :param iface: The interface name.
    :type iface: str
    """
    q = Query()
    table = get_tinydb().table("bridge_ifaces")
    cond = (q.bridge == bridge) & (q.iface == iface)
    removed = table.remove(cond)
    if removed:
        mark_db_dirty()
