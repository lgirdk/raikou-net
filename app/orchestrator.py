"""OVS network orchestration script.

Basic Script that depends on having ovs-vsctl pre-installed in the system.
Need to ensure that the dockerr.socket is mounted else the program must close.
"""

from __future__ import annotations

import asyncio
import ipaddress
import sys
import traceback
from subprocess import CalledProcessError
from typing import Literal, cast

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
    MAX_FAIL_COUNT,
    USE_LINUX_BRIDGE,
    BridgeInfoDict,
    ContainerInfoDict,
    IfaceInfoDict,
    auto_allocate_ip,
    check_container_exists,
    get_config,
    get_db,
    get_logger,
    get_usb_interface,
    run_command,
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

    _LOGGER.debug("Trying to bring up parent %s for bridge %s", parent, bridge_name)
    run_command(f"ip link set {parent} up")

    if USE_LINUX_BRIDGE:
        add_iface_to_linux_bridge(bridge_name, parent_info)
    else:
        add_iface_to_ovs_bridge(bridge_name, parent_info)


def init_bridge(bridge_name: str, info: BridgeInfoDict) -> None:
    """Create an OVS/Linux bridge if it does not exist.

    If a parent interface is provided as part of the OVS bridge info,
    then it shall be a member of the bridge.

    The trunk and native VLAN details are associated to the parent port in OVS.

    :param bridge_name: OVS bridge name
    :type bridge_name: str
    :param info: OVS/Linux bridge details
    :type info: BridgeInfoDict
    :raises ValueError: If IP address is already allocated/incorrect.
    """
    _LOGGER.debug("################## OVS BRIDGES #####################")
    db_cache = get_db(bridge_name)

    # Create the Linux/OVS bridge
    create_bridge(bridge_name)

    # Update bridge specific IP address range and Host details
    for range_key, ip_addr in (
        ("iprange", info.get("ipaddress")),
        ("ip6range", info.get("ip6address")),
    ):
        if (ip_range := info.get(range_key)) != db_cache.get(range_key):
            # Since IP range in cache is getting updated,
            # remove all previous host reservations.

            _LOGGER.debug("Updating IP range for %s to %s", bridge_name, ip_range)
            db_cache[range_key] = ip_range
            db_cache[f"{range_key}_hosts"] = {}

        hosts = db_cache.setdefault(f"{range_key}_hosts", {})
        family = "-4" if range_key == "iprange" else "-6"

        if not ip_addr:
            # If ip_addr is not requested, simply flush and continue
            _LOGGER.debug("Flusing IP address for %s", bridge_name)

            hosts.pop(bridge_name, None)
            run_command(f"ip {family} addr flush dev {bridge_name}", check=False)
            continue

        set_ip, cache_changed = False, False

        if ip_addr != hosts.get(bridge_name):
            # If ipaddress has changed, update the the cache.
            # Will check if the new IP is not in conflict with any other host
            # before assigning to the bridge.
            hosts.pop(bridge_name, None)
            run_command(f"ip {family} addr flush dev {bridge_name}", check=False)
            set_ip, cache_changed = True, True

        elif ip_addr not in get_interface_ip(bridge_name):
            # If for some reason, ipaddress on the bridge interface
            # is lost, re-add the ip again.
            set_ip = True

        if set_ip:
            if cache_changed and ip_addr in hosts.values():
                msg_set_ip_err = (
                    f"IP {ip_addr} already allocated to someone else. ",
                    f"Cannot assign request address to bridge {bridge_name}",
                )
                raise ValueError(msg_set_ip_err)

            if ipaddress.ip_interface(ip_addr) not in ipaddress.ip_network(
                str(ip_range)
            ):
                # Ensure that IP address provided by user is always
                # part of the same range as that being maintained by the bridge.
                msg = f"{ip_addr} does not fall under the range {ip_range}"
                raise ValueError(msg)

            hosts[bridge_name] = ip_addr
            run_command(f"ip addr add {ip_addr} dev {bridge_name}")
            _LOGGER.info("Updated IP address for %s to %s", bridge_name, ip_addr)

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

    :param container_name: Target container to push the interface at
    :type container_name: str
    :param info: Container interface details
    :type info: ContainerInfoDict
    :raises ValueError: If ipaddress syntax is incorrect.
    """
    _LOGGER.debug("###################ADD IFACE TO CONTAINERS######################")

    util = "ovs-docker" if not USE_LINUX_BRIDGE else "lxbr-docker"
    bridge = info["bridge"]  # Mandatory
    iface = info["iface"]  # Mandatory
    db_cache = get_db(bridge)
    cc_cache = db_cache.setdefault(container_name, {})
    cmd = f"{util} add-port {bridge} {iface} {container_name}"
    cc_cache.setdefault(iface, {})

    # Check if container exists, skip if it does not exist.
    if (not check_container_exists(container_name)) or check_interface_exists(
        bridge, container_name, iface, util
    ):
        # If interface already exists, we exit
        # Note: Need to add checks for IP address too before exiting.
        return

    for prefix in ("ip", "ip6"):
        address_key = f"{prefix}address"
        range_key = f"{prefix}range"
        hosts = db_cache.get(f"{range_key}_hosts", {})
        if not (ipaddr := info.get(address_key)):
            # If ipaddress is not provided, but the bridge has an iprange defined
            # The container will be provided with an IP address from  bridge's
            # ip range.
            if db_cache.get(range_key):
                ip = auto_allocate_ip(bridge, container_name, prefix)
                cmd = f"{cmd} --{address_key}={ip}"
            continue

        if ipaddr == "No-IP":  # If the user explicitly specifies "No-IP"
            continue  # Then skip

        if "/" not in str(ipaddr):
            msg_no_prefix = f"{container_name}: ip {ipaddr} must have a prefix mask"
            raise ValueError(msg_no_prefix)

        if ipaddr != hosts.get(container_name):
            hosts.pop(container_name, None)
            if ipaddr in hosts.values():
                msg_ip_exists = (
                    f"IP {ipaddr} already allocated to someone else.",
                    f"Failed to assign addr to container: {container_name}",
                )
                raise ValueError(msg_ip_exists)

        hosts[container_name] = ipaddr
        cmd = f"{cmd} --{address_key}={ipaddr}"

    for key in ["macaddress", "gateway", "gateway6"]:
        # Note: add a check here to ensure that
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


async def main() -> None:  # noqa: C901
    """Runner function that runs in a loop."""
    # Initial Check if docker socket is loaded.
    if not DOCKER_SOCKET.exists():
        _LOGGER.error("Need to mount Docker socket!!")
        sys.exit(1)

    check_sys_module()

    fail_count = cast(int, get_db("failed", 0))

    while True:
        config = get_config()

        if fail_count > MAX_FAIL_COUNT:
            sys.exit(1)
        try:
            async with EVENT_LOCK:
                # Initialize all parent bridges
                for bridge, info in config["bridge"].items():
                    init_bridge(bridge, info)

                # Attach containers to parent bridges based on config.json
                for container, iface_info in config["container"].items():
                    for info in iface_info:
                        add_iface_to_container(container, info)

                # Handle Veth pairs and VLAN translations
                for prefix, translation in config.get("veth_pairs", {}).items():
                    create_veth_pair(
                        on_bridge=translation["on"],
                        prefix=prefix,
                        vlan_map=translation.get("map", ":"),
                        trunk=translation.get("trunk", "no"),
                    )

            # Introduce a sleep to wait before the next loop cycle
            await asyncio.sleep(15)  # This allows cancellation to be checked

        except asyncio.CancelledError:
            _LOGGER.info("Main loop has been cancelled. Shutting down gracefully.")

        except (CalledProcessError, ValueError, IndexError):
            _LOGGER.exception("Exiting core due to exception")
            traceback.print_exc()
            get_db()["failed"] = fail_count + 1
            if fail_count > MAX_FAIL_COUNT:
                _LOGGER.exception("Orchestrator keeps failing! Exiting.")
                sys.exit(1)
