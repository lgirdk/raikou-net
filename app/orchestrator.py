"""OVS network orchestration script.

Basic Script that depends on having ovs-vsctl pre-installed in the system.
Need to ensure that the dockerr.socket is mounted else the program must close.
"""

from __future__ import annotations

import asyncio
import ipaddress
import traceback
from subprocess import CalledProcessError
from typing import Literal

from app.ovs_lib import (
    add_iface_to_linux_bridge,
    add_iface_to_ovs_bridge,
    check_interface_exists,
    check_sys_module,
    configure_container_vlan,
    create_bridge,
    get_interface_ip,
    veth_exists,
)
from app.utils import (
    DOCKER_SOCKET,
    EVENT_LOCK,
    USE_LINUX_BRIDGE,
    BridgeInfoDict,
    ContainerInfoDict,
    IfaceInfoDict,
    auto_allocate_ip,
    bootstrap_runtime_config,
    check_container_exists,
    clear_bridge_host,
    clear_bridge_hosts,
    clear_bridge_iface,
    clear_container_iface,
    get_all_container_ifaces,
    get_all_veth_ifaces,
    get_bridge,
    get_bridge_hosts,
    get_config,
    get_logger,
    get_usb_interface,
    ingress_external_config,
    mark_tick_success,
    maybe_flush_state,
    run_command,
    save_runtime_config,
    set_bridge_host,
    upsert_bridge,
    upsert_container_iface,
)

_LOGGER = get_logger("orchestrator")


def _add_iface_to_bridge(bridge_name: str, parent_info: IfaceInfoDict) -> None:
    """Add a network interface to an OVS bridge.

    :param bridge_name: The name of the OVS bridge.
    :type bridge_name: str
    :param parent_info: The OVS/Linux bridge parent details.
    :type parent_info: IfaceInfoDict
    """
    if (parent := parent_info.get("iface")) is None:
        _LOGGER.debug("Invalid Entry: %s \nSkipping ..", str(parent_info))
        return

    if "usb:" in parent:
        parent_info["iface"] = get_usb_interface(parent.split(":")[-1])
        parent = parent_info["iface"]

    _LOGGER.debug("Trying to bring up parent %s for bridge %s", parent, bridge_name)
    run_command(f"ip link set {parent} up")

    if USE_LINUX_BRIDGE:
        add_iface_to_linux_bridge(bridge_name, parent_info)
    else:
        add_iface_to_ovs_bridge(bridge_name, parent_info)


def _apply_bridge_ip(
    bridge_name: str,
    family: str,
    ip_addr: str,
    new_range: str | None,
) -> None:
    """Assign *ip_addr* to *bridge_name* after conflict and range checks.

    Called only when ``init_bridge`` determines the address must change.

    :param bridge_name: The name of the bridge to assign the IP to.
    :type bridge_name: str
    :param family: Address family — `"ip"` for IPv4 or `"ip6"` for IPv6.
    :type family: str
    :param ip_addr: The IP address (with prefix) to assign to the bridge.
    :type ip_addr: str
    :param new_range: The IP range the address must fall within, or None.
    :type new_range: str | None
    :raises ValueError: If the IP is already allocated to another host or falls outside the range.
    """
    ip_family_flag = "-4" if family == "ip" else "-6"
    hosts = get_bridge_hosts(bridge_name, family)
    cache_changed = ip_addr != hosts.get(bridge_name)

    if cache_changed:
        clear_bridge_host(bridge_name, bridge_name, family)
        run_command(f"ip {ip_family_flag} addr flush dev {bridge_name}", check=False)
        hosts = get_bridge_hosts(bridge_name, family)

    if not cache_changed and ip_addr in get_interface_ip(bridge_name):
        return  # already correct on the interface — nothing to do

    if cache_changed and ip_addr in hosts.values():
        msg = (
            f"IP {ip_addr} already allocated to someone else. "
            f"Cannot assign request address to bridge {bridge_name}"
        )
        raise ValueError(msg)

    if ipaddress.ip_interface(ip_addr) not in ipaddress.ip_network(str(new_range)):
        msg = f"{ip_addr} does not fall under the range {new_range}"
        raise ValueError(msg)

    set_bridge_host(bridge_name, bridge_name, family, ip_addr)
    run_command(f"ip addr add {ip_addr} dev {bridge_name}")
    _LOGGER.info("Updated IP address for %s to %s", bridge_name, ip_addr)


def init_bridge(bridge_name: str, info: BridgeInfoDict) -> None:
    """Create an OVS/Linux bridge if it does not exist.

    Idempotent: re-runs on every reconcile tick. Diff-aware accessors make
    the no-change case a no-op (no `mark_db_dirty` calls).

    :param bridge_name: The name of the bridge to create or reconcile.
    :type bridge_name: str
    :param info: The bridge configuration dict (parents, iprange, ip6range, etc.).
    :type info: BridgeInfoDict
    """
    _LOGGER.debug("################## OVS BRIDGES #####################")
    bridge_row = get_bridge(bridge_name) or {}

    # Create the Linux/OVS bridge
    create_bridge(bridge_name)

    # Update bridge specific IP address range and Host details
    for range_key, ip_addr in (
        ("iprange", info.get("ipaddress")),
        ("ip6range", info.get("ip6address")),
    ):
        family = "ip" if range_key == "iprange" else "ip6"
        ip_family_flag = "-4" if family == "ip" else "-6"
        new_range = info.get(range_key)

        if new_range != bridge_row.get(range_key):
            _LOGGER.debug("Updating IP range for %s to %s", bridge_name, new_range)
            upsert_bridge(bridge_name, **{range_key: new_range})
            clear_bridge_hosts(bridge_name, family)
            # Refresh local view after writes
            bridge_row = get_bridge(bridge_name) or {}

        hosts = get_bridge_hosts(bridge_name, family)

        if not ip_addr:
            _LOGGER.debug("Flushing IP address for %s", bridge_name)
            if bridge_name in hosts:
                clear_bridge_host(bridge_name, bridge_name, family)
            run_command(
                f"ip {ip_family_flag} addr flush dev {bridge_name}", check=False
            )
            continue

        _apply_bridge_ip(bridge_name, family, ip_addr, new_range)

    # Add parent interfaces
    for parent_info in info.get("parents", []):
        _add_iface_to_bridge(bridge_name=bridge_name, parent_info=parent_info)


def create_veth_pair(
    on_bridge: str, prefix: str, vlan_map: str = ":", trunk: Literal["yes", "no"] = "no"
) -> None:
    """Create a veth pair and attach it to OVS bridges.

    Create a veth pair and attach each end of the pair to the OVS bridge with
    the name ```on_bridge``` .

    Set VLAN tags on each end based on the `vlan_map`.

    The function follows the following rules:
    - If the veth pair already exists, it is assumed that both ends are created.
    - The veth endpoints are attached to the specific bridges.
    - VLAN tags are set on the bridge interfaces.
    - The external_ids are set to track the VLAN translation.

    :param on_bridge: OVS bridge to attach the first veth end.
    :type on_bridge: str
    :param prefix: prefix name to add for veth interfaces
    :type prefix: str
    :param vlan_map: Optional, VLAN mapping in the format "source_vlan:dest_vlan".
    :type vlan_map: str
    :param trunk: If ports should be added to bridge as trunk. Default is no.
    :type trunk: Literal["yes", "no"]
    :raises ValueError: if prefix length is more than 8 characters
    """
    _LOGGER.debug("################## VLAN TRANSLATION #####################")
    prefix_length = 8
    if len(prefix) > prefix_length:
        msg = f"VETH prefix: {prefix} cannot be more than 8 characters."
        raise ValueError(msg)

    veth0 = f"v0_{prefix}"
    veth1 = f"v1_{prefix}"
    _LOGGER.debug("VETH pair entry: %s <--> %s", veth0, veth1)
    log_method = _LOGGER.info

    # Check if veth pair already exists
    # We will always check the C-VLAN veth endpoint.
    if not veth_exists(veth0):
        # Create veth pair
        run_command(f"ip link add {veth0} type veth peer name {veth1}")
        run_command(f"ip link set dev {veth0} up")
        run_command(f"ip link set dev {veth1} up")

        _LOGGER.info("VETH pair created: %s <--> %s", veth0, veth1)
    else:
        _LOGGER.debug(
            "VETH pair %s <--> %s  exists on the host!!",
            veth0,
            veth1,
        )
        _LOGGER.debug("Skipping VLAN endpoint creation.")
        log_method = _LOGGER.debug

    add_function = (
        add_iface_to_linux_bridge if USE_LINUX_BRIDGE else add_iface_to_ovs_bridge
    )

    # Split the vlan_map to check if VLAN needs to be configured
    source_vlan, dest_vlan = vlan_map.split(":")
    _LOGGER.debug("VLAN mapping %s on %s", vlan_map, on_bridge)

    # Always attach the first veth (veth0) to the bridge
    _LOGGER.debug("Attaching %s to bridge %s", veth0, on_bridge)
    if trunk == "yes":
        add_function(on_bridge, {"iface": veth0, "trunk": source_vlan})
    else:
        add_function(on_bridge, {"iface": veth0, "vlan": source_vlan})
    log_method("VETH %s attached to bridge %s", veth0, on_bridge)

    if dest_vlan:
        _LOGGER.debug("Attaching %s to bridge %s", veth1, on_bridge)
        if trunk == "yes":
            add_function(on_bridge, {"iface": veth1, "trunk": dest_vlan})
        else:
            add_function(on_bridge, {"iface": veth1, "vlan": dest_vlan})
        log_method("VETH %s attached to bridge %s", veth1, on_bridge)
    else:
        _LOGGER.debug("No VLAN configuration for veth1: %s", veth1)
        log_method("VETH %s is dangling!", veth1)


def add_iface_to_container(  # noqa: C901
    container_name: str,
    info: ContainerInfoDict,
) -> None:
    """Attach a container to a target OVS bridge.

    :param container_name: The name of the container to attach the interface to.
    :type container_name: str
    :param info: The container interface configuration dict (bridge, iface, ip, etc.).
    :type info: ContainerInfoDict
    :raises ValueError: If the IP address lacks a prefix mask or is already allocated to another container.
    """
    _LOGGER.debug("###################ADD IFACE TO CONTAINERS######################")

    util = "ovs-docker" if not USE_LINUX_BRIDGE else "lxbr-docker"
    bridge = info["bridge"]  # Mandatory
    iface = info["iface"]  # Mandatory
    cmd = f"{util} add-port {bridge} {iface} {container_name}"

    # Ensure a container_ifaces row exists (no VLAN fields yet — those land in
    # configure_container_vlan via ovs_lib).
    upsert_container_iface(bridge, container_name, iface)

    # Check if container exists, skip if it does not exist.
    if (not check_container_exists(container_name)) or check_interface_exists(
        bridge, container_name, iface, util
    ):
        return

    for prefix in ("ip", "ip6"):
        address_key = f"{prefix}address"
        range_key = f"{prefix}range"
        hosts = get_bridge_hosts(bridge, prefix)
        if not (ipaddr := info.get(address_key)):
            bridge_row = get_bridge(bridge) or {}
            if bridge_row.get(range_key):
                ip = auto_allocate_ip(bridge, container_name, prefix)
                cmd = f"{cmd} --{address_key}={ip}"
            continue

        if ipaddr == "No-IP":
            continue

        if "/" not in str(ipaddr):
            msg_no_prefix = f"{container_name}: ip {ipaddr} must have a prefix mask"
            raise ValueError(msg_no_prefix)

        if ipaddr != hosts.get(container_name):
            if container_name in hosts and hosts[container_name] != ipaddr:
                clear_bridge_host(bridge, container_name, prefix)
                hosts = get_bridge_hosts(bridge, prefix)
            if ipaddr in hosts.values():
                msg_ip_exists = (
                    f"IP {ipaddr} already allocated to someone else.",
                    f"Failed to assign addr to container: {container_name}",
                )
                raise ValueError(msg_ip_exists)

        set_bridge_host(bridge, container_name, prefix, ipaddr)
        cmd = f"{cmd} --{address_key}={ipaddr}"

    for key in ["macaddress", "gateway", "gateway6"]:
        if value := info.get(key, ""):
            cmd = f"{cmd} --{key}={value}"

    run_command(cmd)
    _LOGGER.info(
        "Interface %s connected to bridge:%s added to container %s",
        iface,
        bridge,
        container_name,
    )
    configure_container_vlan(container_name, info)


def remove_container_iface(container_name: str, bridge: str, iface: str) -> None:
    """Detach a container interface and clean up IP allocations and DB tracking.

    Runs del-port, frees IP allocations for both address families, and removes
    the DB tracking row. If del-port fails (e.g. container already gone),
    cleanup still proceeds.

    :param container_name: The container to detach from.
    :type container_name: str
    :param bridge: The bridge the interface is on.
    :type bridge: str
    :param iface: The interface name inside the container.
    :type iface: str
    """
    util = "ovs-docker" if not USE_LINUX_BRIDGE else "lxbr-docker"
    try:
        run_command(f"{util} del-port {bridge} {iface} {container_name}")
    except CalledProcessError:
        _LOGGER.warning(
            "del-port %s %s %s failed — container may be gone; proceeding with cleanup",
            bridge,
            iface,
            container_name,
        )
    clear_bridge_host(bridge, container_name, "ip")
    clear_bridge_host(bridge, container_name, "ip6")
    clear_container_iface(bridge, container_name, iface)
    _LOGGER.info(
        "Removed interface %s from container %s on bridge %s",
        iface,
        container_name,
        bridge,
    )


def remove_veth_pair(prefix: str, bridge: str) -> None:
    """Remove a veth pair from its bridge and delete both ends.

    Detaches v0_{prefix} from the bridge, deletes the veth pair kernel objects,
    and clears both DB rows. If the veth is already gone, cleanup still proceeds.

    :param prefix: The veth pair prefix (<=8 chars). Manages v0_{prefix} / v1_{prefix}.
    :type prefix: str
    :param bridge: The bridge v0_{prefix} is attached to.
    :type bridge: str
    """
    veth0 = f"v0_{prefix}"
    veth1 = f"v1_{prefix}"
    try:
        if USE_LINUX_BRIDGE:
            run_command(f"brctl delif {bridge} {veth0}")
        else:
            run_command(f"ovs-vsctl del-port {bridge} {veth0}")
    except CalledProcessError:
        _LOGGER.warning(
            "Bridge del-port for %s on %s failed — may already be detached; proceeding",
            veth0,
            bridge,
        )
    try:
        run_command(f"ip link delete {veth0}")
    except CalledProcessError:
        _LOGGER.warning("ip link delete %s failed — may already be gone", veth0)
    clear_bridge_iface(bridge, veth0)
    clear_bridge_iface(bridge, veth1)
    _LOGGER.info("Removed veth pair %s <--> %s from bridge %s", veth0, veth1, bridge)


def removal_pass(config: dict) -> None:
    """Remove interfaces and veth pairs no longer present in desired config.

    Called at the end of each reconcile tick after all add passes. Compares
    the ``container_ifaces`` and ``bridge_ifaces`` DB tables against the
    in-memory config; tears down anything tracked in the DB but absent from
    config. Errors are caught per-row so one failure does not block others.

    :param config: The live in-memory config dict from ``get_config()``.
    :type config: dict
    """
    for row in get_all_container_ifaces():
        bridge: str = row["bridge"]
        container: str = row["container"]
        iface: str = row["iface"]
        desired = config.get("container", {}).get(container, [])
        if not any(
            e.get("bridge") == bridge and e.get("iface") == iface for e in desired
        ):
            _LOGGER.info(
                "Removal pass: removing stale iface %s/%s from container %s",
                bridge,
                iface,
                container,
            )
            try:
                remove_container_iface(container, bridge, iface)
            except (CalledProcessError, ValueError, IndexError, KeyError):
                _LOGGER.exception(
                    "Failed to remove iface %s/%s/%s", bridge, container, iface
                )
                continue
            if not config.get("container", {}).get(container):
                config.get("container", {}).pop(container, None)
                save_runtime_config()

    for row in get_all_veth_ifaces():
        prefix: str = row["iface"].removeprefix("v0_")
        bridge: str = row["bridge"]
        if prefix not in config.get("veth_pairs", {}):
            _LOGGER.info(
                "Removal pass: removing stale veth pair %s from bridge %s",
                prefix,
                bridge,
            )
            try:
                remove_veth_pair(prefix, bridge)
            except (CalledProcessError, ValueError, IndexError, KeyError):
                _LOGGER.exception("Failed to remove veth pair %s/%s", prefix, bridge)


async def main() -> None:
    """Reconcile loop. Owns no supervision state — runner handles crash policy.

    :raises RuntimeError: If the Docker socket is not mounted at startup.
    :raises asyncio.CancelledError: When the task is cancelled during shutdown.
    """
    if not DOCKER_SOCKET.exists():
        _LOGGER.error("Need to mount Docker socket!!")
        msg = "Docker socket missing"
        raise RuntimeError(msg)

    check_sys_module()
    bootstrap_runtime_config()

    while True:
        try:
            async with EVENT_LOCK:
                ingress_external_config()
                config = get_config()

                for bridge, info in config["bridge"].items():
                    init_bridge(bridge, info)

                for container, iface_info in config["container"].items():
                    for info in iface_info:
                        add_iface_to_container(container, info)

                for prefix, translation in config.get("veth_pairs", {}).items():
                    create_veth_pair(
                        on_bridge=translation["on"],
                        prefix=prefix,
                        vlan_map=translation.get("map", ":"),
                        trunk=translation.get("trunk", "no"),
                    )

                removal_pass(config)
                maybe_flush_state()

            mark_tick_success()
            await asyncio.sleep(15)

        except asyncio.CancelledError:
            _LOGGER.info("Main loop cancelled; propagating")
            raise

        except (CalledProcessError, ValueError, IndexError, KeyError):
            _LOGGER.exception("Recoverable error in reconcile tick")
            traceback.print_exc()
            await asyncio.sleep(15)
