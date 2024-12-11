"""OVS network orchestration utils.

This part includes utilities, logging setup, and schema definitions.
Provides a logger provider function for use in other modules.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import sys
from functools import cache
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Any, TypedDict, TypeVar

# Constants
DB_JSON_PATH = Path("/tmp/db.json")  # noqa: S108
MAX_FAIL_COUNT = 2
DOCKER_SOCKET = Path("/var/run/docker.sock")
USE_LINUX_BRIDGE = os.environ.get("USE_LINUX_BRIDGE", "false") in ("true", "1")
EVENT_LOCK = asyncio.Lock()
T = TypeVar("T")


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


# Cache function to get the OVS database from JSON file
@cache
def _open_db() -> dict[str, Any]:
    return json.load(DB_JSON_PATH.open(encoding="utf-8"))


def get_db(key: str = "", default: T | None = None) -> dict[str, Any] | T:
    """Retrieve the OVS database cache or a specific section of it.

    This function returns the full OVS database cache if no key is provided.
    If a key is specified, it returns the corresponding section of the cache.
    If the key does not exist in the database, the provided `default` value is used
    (an empty dictionary by default).

    :param key: Optional. The key for a specific section of the database.
    :type key: str
    :param default: Optional. The default value to set if the key does not exist.
    :type default: Any
    :return: The full OVS database cache or the section specified by the key.
    :rtype: dict[str, Any] | Any
    """
    db = _open_db()
    if key:
        # Only set to an empty dict if `default` is not provided.
        return db.setdefault(key, default if default is not None else {})
    return db


@cache
def get_config() -> dict[str, Any]:
    """Return the OVS config.

    :return: The OVS config.
    :rtype: dict[str, Any]
    """
    with Path("/root/config.json").open(encoding="UTF-8") as fp:
        return json.load(fp)


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
        stderr_output = exc.stderr if exc.stderr else None
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

    :param bridge_name: The brigde name to allocate IP from for the container.
    :type bridge_name: str
    :param container_name: Name of the container to assign the IP to.
    :type container_name: str
    :param family: The IP family to allocate from ("ip" for IPv4 or "ip6" for IPv6).
                   Default is "ip".
    :type family: str
    :raises IndexError: If no available IP addresses remain in the range.
    :return: The allocated IP address with the correct prefix.
    :rtype: str
    """
    db_cache = get_db(bridge_name)
    ip_range = db_cache.get(f"{family}range", "/24")
    hosts = db_cache.get(f"{family}range_hosts", {})

    network_hosts = ipaddress.ip_network(str(ip_range)).hosts()
    _ = [next(network_hosts) for _ in range(5)]  # Skip first 5 addresses

    for host in network_hosts:
        ipaddr = f"{host}/{ip_range.split('/')[-1]}"
        if ipaddr not in hosts.values():
            _LOGGER.debug(
                "Automatic IP allocation (%s) to container: %s", ipaddr, container_name
            )
            hosts[container_name] = ipaddr
            return ipaddr

    msg = f"Failed to automatically allocate an IP to container: {container_name}"
    raise IndexError(msg)


def validate_bridge(bridge_name: str, info: BridgeInfoDict) -> bool:
    """Validate if a bridge already exists in the database.

    If any of its parent interfaces are already part of the existing bridge,
    then the validation fails

    :param bridge_name: The name of the bridge to be validated.
    :param info: A dictionary containing the bridge's information,
                 including its parent interfaces.
    :return: True if the bridge does not exist or
             no parent interfaces are conflicting,
             False otherwise.
    """
    if bridge := get_db(bridge_name):
        _LOGGER.debug("Bridge Already exists: %s", bridge_name)
        for parent in info["parents"]:
            if parent["iface"] in bridge:
                _LOGGER.error(
                    "iface %s exists in bridge: %s",
                    parent["iface"],
                    bridge_name,
                )
                return False
    return True


def validate_container(container_id: str, info: ContainerInfoDict) -> bool:
    """Validate if the specified container's interface already exists.

    This function checks whether the given container's interface (`iface`)
    is already present for the specified container in the associated bridge.
    If the interface exists, it logs an error and returns `False`.

    :param container_id: container name
    :type container_id: str
    :param info: container's information, including its bridge and
                 interface details.
    :type info: ContainerInfoDict
    :return: True if container interface does not exists.
    """
    db = get_db(info["bridge"])
    if (cc_cache := db.get(container_id, {})) and info["iface"] in cc_cache:
        _LOGGER.error(
            "iface %s already exists for container: %s",
            info["iface"],
            container_id,
        )
        return False
    return True


def validate_veth_pair(veth_pair_id: str, info: dict) -> bool:
    """Validate the VETH pair ID.

    This function performs two checks:

    1. Ensures that the `veth_pair_id` does not exceed the
       predefined length limit of 8 characters.
    2. Checks if the VETH pair's interface name (e.g., `v0_{veth_pair_id}`)
       already exists on the specified bridge.

    If any validation fails, it logs an error and returns `False`.
    Otherwise, it returns `True`.

    :param veth_pair_id: The unique identifier for the VETH pair,
                         which will be used as a prefix.
    :type veth_pair_id: str
    :param info: Dictionary containing details about the VETH pair,
                 including the target bridge (`info["on"]`).
    :type info: dict
    :return: Returns `True` if the validation passes, otherwise `False`.
    :rtype: bool
    """
    prefix_length_limit = 8
    if len(veth_pair_id) > prefix_length_limit:
        _LOGGER.error("VETH prefix ID: %s is more than 8 chars", veth_pair_id)
        return False

    veth_pair_end = f"v0_{veth_pair_id}"
    if (bridge := get_db(info["on"])) and veth_pair_end in bridge:
        _LOGGER.error(
            "iface %s exists in bridge: %s",
            veth_pair_id,
            info["on"],
        )
        return False
    return True
