"""OVS network orchestration helper functions.

This part contains public helper functions for command execution, IP retrieval,
and OVS database management.
"""

import re
import sys
from subprocess import CalledProcessError, run

from app.utils import (
    USE_LINUX_BRIDGE,
    ContainerInfoDict,
    IfaceInfoDict,
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


def remove_linux_bridge_vlan(iface: str, vid: str) -> bool:
    """Remove or reset the specified VLAN setting from a Linux bridge interface.

    This function checks the current VLAN setting on a Linux bridge interface. If the
    current value does not match the provided `vid`, it removes or resets
    the VLAN settings (trunk, native, or tagged VLAN) for the specified interface.

    :param iface: The network interface from which to remove the VLAN setting.
    :type iface: str
    :param vid: The VLAN ID to be removed.
    :type vid: str
    :return: True if VLAN settings were removed, False if there was no change.
    :rtype: bool
    """
    # Determine the current VLAN settings on the interface using `bridge vlan`
    check = run_command(f"bridge vlan show dev {iface}", check=False)

    if not check.stdout.strip():
        _LOGGER.debug("No VLAN settings found on iface %s", iface)
        return True

    # Split the expected and actual VLANs
    expected_values = set(vid.split(","))
    actual_values = [
        re.findall(r"\d+", li).pop()
        for li in check.stdout.strip().splitlines()[1:]
        if re.findall(r"\d+", li)
    ]

    # Find any VLANs that exist but aren't expected
    actual_value_set = set(actual_values)
    to_remove = actual_value_set - expected_values

    # If all actual values are as expected, no need to remove anything
    if not to_remove:
        _LOGGER.info(
            "Current VLAN settings for iface %s match the expected: %s",
            iface,
            actual_values,
        )
        return False

    _LOGGER.info("VLAN settings to be removed from iface %s: %s", iface, to_remove)

    # Remove any VLANs that are not in the expected values
    for vlan_id in to_remove:
        _LOGGER.info("Removing VLAN: %s from iface %s", vlan_id, iface)
        cmd = f"bridge vlan del vid {vlan_id} dev {iface}"
        run_command(cmd)

    return True


def remove_ovs_vlan_port(parent: str, vlan_type: str, vid: str) -> bool:
    """Remove or reset the specified VLAN setting from the OVS port if the value differs.

    This function checks the current VLAN setting on the OVS port. If the
    current value does not match the provided `value`, it removes or resets
    the VLAN settings (trunk, native, or tagged VLAN) for the specified interface
    on the OVS bridge.

    :param parent: The interface (port) from which to remove the VLAN setting.
    :type parent: str
    :param vlan_type: The VLAN setting type (trunk, native, vlan).
    :type vlan_type: str
    :param vid: The value of the VLAN setting to be removed.
    :type vid: str
    :return: True if VLAN settings were removed.
    :rtype: bool
    """
    # Get the current configuration for the port
    if vlan_type == "trunk":
        check = run_command(f"ovs-vsctl get port {parent} trunks", check=False)
        current_value = re.findall(r"\d+", check.stdout.strip())
        _LOGGER.debug("Current trunk VLAN for port %s is %s", parent, current_value)
    elif vlan_type in ("native", "vlan"):
        check = run_command(f"ovs-vsctl get port {parent} tag", check=False)
        current_value = re.findall(r"\d+", check.stdout.strip())
        _LOGGER.debug("Current tag VLAN for port %s is %s", parent, current_value)

    # if there is no setting, then there was nothing to remove.
    if not current_value:
        return True

    # Check if the current value differs from the one we want to remove
    if set(current_value) == set(re.findall(r"\d+", vid)):
        _LOGGER.info(
            "No need to remove %s VLAN setting %s for port %s, already set",
            vlan_type,
            vid,
            parent,
        )
        return False

    # Remove the VLAN configuration only if it doesn't match
    if vlan_type == "trunk":
        _LOGGER.debug("Removing trunk VLAN setting from port %s", parent)
        run_command(f"ovs-vsctl remove port {parent} trunks {','.join(current_value)}")
    elif vlan_type in ("native", "vlan"):
        _LOGGER.debug("Removing VLAN tag setting from port %s", parent)
        run_command(f"ovs-vsctl remove port {parent} tag {','.join(current_value)}")

    _LOGGER.info(
        "%s VLAN setting %s removed from port %s",
        vlan_type.capitalize(),
        current_value,
        parent,
    )
    return True


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

    # This means that the interface was part of the wrong module
    # eg. if the interface was part of linux when meant to be part of OVS
    if run_command(f"ip link show dev {bridge_name}", check=False).returncode == 0:
        _LOGGER.debug("Bridge %s already exists but not on right module", bridge_name)
        run_command(f"ip link set {bridge_name} down")
        run_command(f"ovs-vsctl del-br {bridge_name}", check=False)
        run_command(f"brctl delbr {bridge_name}", check=False)
        _LOGGER.info("Removed redundant Bridge %s", bridge_name)

    # Bridge doesn't exist, create it
    cmd, check = f"ovs-vsctl --may-exist add-br {bridge_name}", True
    if USE_LINUX_BRIDGE:
        cmd, check = f"brctl addbr {bridge_name}", False
    run_command(cmd, check)
    run_command(f"ip link set {bridge_name} up")
    _LOGGER.info("Bridge %s created and brought up", bridge_name)


def add_iface_to_ovs_bridge(bridge_name: str, iface_info: IfaceInfoDict) -> None:
    """Add a parent/native interface to an OVS bridge.

    Use this to allow access to public network via your OVS bridge.
    Parent info should hold details of the network interface that connects
    to the public network.

    :param bridge_name: Name of the OVS bridge
    :type bridge_name: str
    :param iface_info: Host interface details
    :type iface_info: IfaceInfoDict
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
        value = iface_info.get(key)
        cleaned_something = remove_ovs_vlan_port(parent, key, str(value))
        if value and value != iface_cache.get(key):
            _LOGGER.info("New %s %s setting applied for parent %s", key, value, parent)
            iface_cache[key] = value
            if cleaned_something:
                configure_ovs_vlan_port(parent, key, str(value))


def add_iface_to_linux_bridge(bridge_name: str, iface_info: IfaceInfoDict) -> None:
    """Add a parent/native interface to an Linux bridge.

    Use this to allow access to public network via your Linux bridge.
    Parent info should hold details of the network interface that connects
    to the public network.

    :param bridge_name: Name of the OVS bridge
    :type bridge_name: str
    :param iface_info: Host interface details
    :type iface_info: IfaceInfoDict
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
            if remove_linux_bridge_vlan(parent, str(value)):
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


def configure_container_vlan(container_name: str, info: ContainerInfoDict) -> None:
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
    :type info: ContainerInfoDict
    """
    util = "ovs-docker" if not USE_LINUX_BRIDGE else "lxbr-docker"
    bridge = info["bridge"]  # Mandatory
    iface = info["iface"]  # Mandatory

    for vlan_mode in ("vlan", "trunk"):
        if value := info.get(vlan_mode):
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
