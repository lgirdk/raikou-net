"""OVS network orchestration helper functions.

This part contains public helper functions for command execution, IP retrieval,
and OVS database management.
"""

import re
import sys
from subprocess import CalledProcessError, run

from app.utils import (
    USE_LINUX_BRIDGE,
    ContainerInfo,
    IfaceInfo,
    get_db,
    get_logger,
    run_command,
)

# Initialize logger
_LOGGER = get_logger("ovs_lib")


def get_interface_ip(interface: str) -> list[str | None]:
    """Get the IP address of a network interface.

    :param interface: The name of the network interface.
    :type interface: str
    :return: The IP address of the interface, or None if not found.
    :rtype: list[str | None]
    """
    try:
        command = ["ip", "-o", "addr", "show", interface]
        result = run(command, check=True, capture_output=True, text=True)
        return re.findall(r"inet\d*\s+(\S+)", result.stdout.strip())
    except CalledProcessError as exc:
        _LOGGER.exception("Subprocess error:\nCommand failed: %s", exc.cmd)
        stderr_output = exc.stderr.strip()
        _LOGGER.exception("Command stderr output:\n%s", stderr_output)
    return []


def veth_exists(veth_end: str) -> bool:
    """Check if a veth or veth pair exists.

    :param veth_end: Name of the veth or veth pair end to check.
    :type veth_end: str
    :return: True if the veth or veth pair exists, False otherwise.
    :rtype: bool
    """
    result = run_command(f"ip link show {veth_end}", check=False)
    return result.returncode == 0


def configure_ovs_vlan_port(port_name: str, vlan_type: str, vid: str) -> None:
    """Configure VLAN settings for an OVS bridge.

    This function applies trunk and native VLAN settings to the specified parent interface
    in an OVS bridge.

    :param port_name: Name of the parent interface attached to OVS Bridge.
    :type port_name: str
    :param vlan_type: VLAN configuration key ('trunk' or 'native' or 'vlan').
    :type vlan_type: str
    :param vid: The VLAN ID(s) associated with the parent interface.
    :type vid: str
    """
    if vlan_type == "trunk":
        run_command(f"ovs-vsctl set port {port_name} trunks={vid}")
    elif vlan_type == "vlan":
        run_command(f"ovs-vsctl set port {port_name} tag={vid}")
    elif vlan_type == "native":
        run_command(
            f"ovs-vsctl set port {port_name} vlan_mode=native-untagged tag={vid}"
        )


def configure_lxbr_vlan_port(
    bridge_name: str, port_name: str, vlan_type: str, vid: str
) -> None:
    """Configure VLAN settings for a Linux bridge.

    This function sets up VLAN filtering and adds VLANs to the specified parent interface
    in a Linux bridge.

    :param bridge_name: Name of the Linux bridge.
    :type bridge_name: str
    :param port_name: Name of the parent interface attached to Linux Bridge.
    :type port_name: str
    :param vlan_type: VLAN configuration key ('trunk' or 'native' or 'vlan').
    :type vlan_type: str
    :param vid: The VLAN ID(s) associated with the parent interface.
    :type vid: str
    """
    run_command(f"ip link set {bridge_name} type bridge vlan_filtering 1")
    run_command(f"bridge vlan delete dev {port_name} vid 1")

    for vlan_id in str(vid).split(","):
        cmd = f"bridge vlan add dev {port_name} vid {vlan_id}"
        if vlan_type in ["native", "vlan"]:
            cmd += " pvid untagged"
        run_command(cmd)


def create_bridge(bridge_name: str) -> None:
    """Create an OVS or Linux bridge.

    :param bridge_name: Name of the bridge to create.
    :type bridge_name: str
    """
    bridge_exists_cmd = (
        f"ovs-vsctl br-exists {bridge_name}"
        if not USE_LINUX_BRIDGE
        else f"brctl show {bridge_name}"
    )
    bridge_check = run_command(bridge_exists_cmd, check=False)

    # If the bridge exists, no need to create it again
    if bridge_check.returncode == 0:
        _LOGGER.debug("Bridge %s already exists", bridge_name)
        return

    # Bridge doesn't exist, create it
    cmd, check = f"ovs-vsctl --may-exist add-br {bridge_name}", True
    if USE_LINUX_BRIDGE:
        cmd, check = f"brctl addbr {bridge_name}", False
    run_command(cmd, check)
    run_command(f"ip link set {bridge_name} up")
    _LOGGER.info("Bridge %s created and brought up", bridge_name)


def add_iface_to_ovs_bridge(bridge_name: str, iface_info: IfaceInfo) -> None:
    """Add a parent/native interface to an OVS bridge.

    Use this to allow access to public network via your OVS bridge.
    Parent info should hold details of the network interface that connects
    to the public network.

    :param bridge_name: Name of the OVS bridge
    :type bridge_name: str
    :param iface_info: Host interface details
    :type iface_info: IfaceInfo
    """
    # Check if the interface already exists
    parent = iface_info.get("iface", "")
    db_cache = get_db(bridge_name)
    iface_cache = db_cache.setdefault(parent, {})

    check = run_command(f"ovs-vsctl port-to-br {parent}", check=False)
    if check.stdout.strip() != bridge_name:
        _LOGGER.debug("Parent %s not part of OVS bridge %s", parent, bridge_name)
        run_command(f"ovs-vsctl --if-exists del-port {parent}", check=False)
        run_command(f"ovs-vsctl --may-exist add-port {bridge_name} {parent}")
        _LOGGER.debug("parent %s up for OVS bridge %s", parent, bridge_name)

    for key in ["trunk", "native", "vlan"]:
        if (value := iface_info.get(key)) and value != iface_cache.get(key):
            _LOGGER.info("New %s %s setting applied for parent %s", key, value, parent)
            iface_cache[key] = value
            configure_ovs_vlan_port(parent, key, str(value))


def add_iface_to_linux_bridge(bridge_name: str, iface_info: IfaceInfo) -> None:
    """Add a parent/native interface to an Linux bridge.

    Use this to allow access to public network via your Linux bridge.
    Parent info should hold details of the network interface that connects
    to the public network.

    :param bridge_name: Name of the OVS bridge
    :type bridge_name: str
    :param iface_info: Host interface details
    :type iface_info: IfaceInfo
    """
    parent = iface_info.get("iface", "")
    db_cache = get_db(bridge_name)
    iface_cache = db_cache.setdefault(parent, {})

    check = run_command(f"ip -o link show master {bridge_name}", check=False)
    if parent not in check.stdout:
        _LOGGER.debug("Parent %s not part of Linux bridge %s", parent, bridge_name)
        run_command(f"ip link set dev {parent} nomaster")
        run_command(f"brctl addif {bridge_name} {parent}")

    for key in ["trunk", "native", "vlan"]:
        if (value := iface_info.get(key)) and value != iface_cache.get(key):
            _LOGGER.info("New %s %s setting applied for parent %s", key, value, parent)
            iface_cache[key] = value
            configure_lxbr_vlan_port(bridge_name, parent, key, str(value))


def check_interface_exists(
    bridge: str, container_name: str, iface: str, util: str
) -> bool:
    """Check if the interface exists inside the container and handle cleanup if necessary.

    :param bridge: Name of the bridge.
    :type bridge: str
    :param container_name: Name of the container.
    :type container_name: str
    :param iface: Name of the interface.
    :type iface: str
    :param util: Utility command (ovs-docker or lxbr-docker).
    :type util: str
    :return: True if the interface exists and was already connected, False otherwise.
    :rtype: bool
    """
    check = run_command(
        f"docker exec {container_name} ip link show {iface}", check=False
    )
    if check.returncode == 0:
        _LOGGER.debug("Interface %s exists inside container %s.", iface, container_name)
        check = run_command(f"{util} get-port {container_name} {iface}", check=False)
        if bool(check.stdout.strip()):
            _LOGGER.debug("Interface %s exists on bridge.", iface)
            return True

        # Found a corner case
        # If OVS orchestrator service is restarted,
        # previously deployed containers still have their old interfaces.
        # However, ovs does not have a link to them.
        _LOGGER.debug(
            "Interface %s exists inside container %s, but not on bridge. Removing...",
            iface,
            container_name,
        )
        run_command(f"docker exec {container_name} ip link del {iface}", check=False)

    _LOGGER.info("Container: %s is missing interface %s!!", container_name, iface)
    run_command(f"{util} del-port {bridge} {iface} {container_name}", check=False)
    _LOGGER.info(
        "Removed redundant pair of %s for container: %s from bridge: %s",
        iface,
        container_name,
        bridge,
    )
    return False


def configure_container_vlan(container_name: str, info: ContainerInfo) -> None:
    """Configure VLAN or trunk settings for a container's interface on a bridge.

    This function configures the VLAN or trunk settings for a container's interface
    (`iface`) on a given bridge (`bridge`). The settings are determined from the
    `info` dictionary, which should include the VLAN or trunk configuration. The
    function will apply the specified VLAN or trunk mode to the interface using the
    appropriate tool (`ovs-docker` or `lxbr-docker`), depending on the system's bridge setup.

    :param container_name: The name of the container whose interface is being configured.
    :type container_name: str
    :param info: A dictionary containing the container interface details, including:
                 - `bridge`: The name of the bridge to configure the interface on (str).
                 - `iface`: The name of the interface to configure (str).
                 - `vlan`: Optional. The VLAN ID to set (str or int).
                 - `trunk`: Optional. The trunk configuration to set (str).
    :type info: ContainerInfo
    """
    util = "ovs-docker" if not USE_LINUX_BRIDGE else "lxbr-docker"
    bridge = info["bridge"]  # Mandatory
    iface = info["iface"]  # Mandatory

    for vlan_mode in ("vlan", "trunk"):
        if value := info.get("vlan"):
            _LOGGER.debug(
                "%s read for %s:%s is %s", vlan_mode, container_name, iface, value
            )
            run(
                f"{util} set-{vlan_mode} {bridge} {iface} {container_name} "
                f"{value}".split(),
                check=True,
                capture_output=True,
            )
            _LOGGER.info(
                "%s set for %s:%s is %s", vlan_mode, container_name, iface, value
            )


def check_sys_module() -> None:
    """Check if OVS module is installed."""
    if USE_LINUX_BRIDGE:
        run_command("sysctl net.bridge.bridge-nf-call-iptables=0")
        return

    lsmod_out = run(["/bin/lsmod"], check=True, capture_output=True)
    try:
        run(
            ["grep", "openvswitch"],
            check=True,
            input=lsmod_out.stdout,
            capture_output=True,
        )

    except CalledProcessError:
        _LOGGER.exception("Openvswitch kernel modules need to be mounted from host!!")
        sys.exit(1)
