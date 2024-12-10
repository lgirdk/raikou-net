"""OVS network orchestration utils.

This part includes utilities, logging setup, and schema definitions.
Provides a logger provider function for use in other modules.
"""

from __future__ import annotations

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
