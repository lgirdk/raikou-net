"""OVS network orchestration script.

Basic Script that depends on having ovs-vsctl pre-installed in the system.
Need to ensure that the dockerr.socket is mounted else the program must close.
"""

import json
import subprocess
import ipaddress as ip
import os
import sys
import time
import logging

from pathlib import Path
from typing import TypedDict

_LOGGER = logging.getLogger()
_LOGGER.setLevel(logging.DEBUG)

_HANDLER = logging.StreamHandler(sys.stdout)
_HANDLER.setLevel(logging.DEBUG)

FORMAT = "[%(asctime)s] [%(levelname)s] %(funcName)s:: %(message)s"
_FORMATTER = logging.Formatter(FORMAT)
_HANDLER.setFormatter(_FORMATTER)
_LOGGER.addHandler(_HANDLER)


class OVSBridgeInfo(TypedDict, total=False):
    """Schema for OVS Bridge details."""

    parent: str  # Optional, parent interface OVS speaks to


class OVSInterfaceInfo(TypedDict, total=False):
    """Schema for OVS Interface Bridge details."""

    iface: str  # Interface name inside of container.
    bridge: str  # Bridge name interface needs to be part of
    vlan: str  # Optional, VLAN ID interface should be part of
    trunk: str  # Optional, Comma separated VLAN ids
    ipaddress: str  # Optional, IPv4 address
    ip6address: str  # Optional, IPv6 address
    gateway: str  # Optional, IPv4 gateway address
    gateway6: str  # Optional, IPv6 gateway address
    macaddress: str  # Optional, MAC address for the interface


def init_ovs_bridge(bridge_name: str, info: OVSBridgeInfo) -> None:
    """Create an OVS bridge if it does not exist.

    :param bridge_name: OVS bridge name
    :type bridge_name: str
    :param info: OVS bridge details
    :type info: OVSBridgeInfo
    :raises RuntimeError: If failed to initialize an interface
    """
    cmd = f"ovs-vsctl --may-exist add-br {bridge_name}"
    parent = info.get("parent")
    if parent:
        # Bring up the parent interface up before adding to bridge.
        try:
            subprocess.run(f"ip link set {parent} up".split(), check=True)
        except subprocess.CalledProcessError as exc:
            logging.error("%s interface does not exists!!", parent)
            raise RuntimeError(f"Failed to bring up parent iface {parent}.") from exc

        cmd = f"{cmd} -- --may-exist add-port {bridge_name} {parent}"

    try:
        subprocess.run(cmd.split(), check=True)
        subprocess.run(f"ip link set {bridge_name} up".split(), check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to initialize ovs-bridge {bridge_name}.") from exc


def add_iface_to_container(container_name: str, info: OVSInterfaceInfo) -> None:
    """Attach a container to a target OVS bridge.

    :param container_name: Target container to push the interface at
    :type container_name: str
    :param info: Container interface details
    :type info: OVSInterfaceInfo
    :raises RuntimeError: If failed to add an interface to a container
    :raises ValueError: If ipaddress syntax is incorrect.
    """
    # Check if container exists, skip if it does not exist.
    check = subprocess.run(
        f"docker ps -f name={container_name} -q".split(),
        capture_output=True,
        check=False,
    )
    if not bool(check.stdout):
        return

    bridge = info["bridge"]  # Mandatory
    iface = info["iface"]  # Mandatory
    ipaddress = info.get("ipaddress")
    gateway = info.get("gateway")
    ip6address = info.get("ip6address")
    gateway6 = info.get("gateway6")
    macaddress = info.get("macaddress")
    vlan = info.get("vlan")
    trunk = info.get("trunk")

    cmd = f"ovs-docker add-port {bridge} {iface} {container_name}"
    if ipaddress:
        if "/" not in ipaddress:
            raise ValueError(f"ip {ipaddress} must have a prefix mask")
        if not isinstance(ip.ip_interface(ipaddress), ip.IPv4Interface):
            raise ValueError(f"ipaddress {ipaddress} must be valid IPv4 address")
        cmd = f"{cmd} --ipaddress={ipaddress}"

    if gateway:
        cmd = f"{cmd} --gateway={gateway}"

    if ip6address:
        if "/" not in ip6address:
            raise ValueError(f"ip6 {ip6address} must have a prefix mask")
        if not isinstance(ip.ip_interface(ip6address), ip.IPv6Interface):
            raise ValueError(f"ip6address {ip6address} must be valid IPv6 address")
        cmd = f"{cmd} --ip6address={ip6address}"

    if gateway6:
        cmd = f"{cmd} --gateway6={gateway6}"

    if macaddress:
        cmd = f"{cmd} --macaddress={macaddress}"

    # check if iface exists already inside the container
    # NOTE: at this point we're really not getting into validating IP addresses.
    check = subprocess.run(
        f"docker exec {container_name} ip link show {iface}".split(),
        capture_output=True,
        check=False,
    )
    if check.returncode == 0:
        # Found a corner case
        # If orchestrator restarts containers still have their old interface
        # However, ovs does not have a link to them.
        # In that case we need to clean the container interface ourself.
        check = subprocess.run(
            f"ovs-docker get-port {container_name} {iface}".split(),
            capture_output=True,
            check=False,
        )
        if bool(check.stdout.strip()):
            # If interface exists and OVS link is present, return
            return

        logging.info("###################Captured Logs######################")
        logging.info("Orchestrator must have restarted!!")
        logging.info("Removing iface %s from container: %s", iface, container_name)
        subprocess.run(
            f"docker exec {container_name} ip link del {iface}".split(),
            check=False,
            capture_output=False,
        )
    else:
        logging.info("###################Captured Logs######################")
        logging.info("Container: %s was missing interface %s!!", iface, container_name)

        # del the OVS mapped port
        # If container has lost its interface
        subprocess.run(
            f"ovs-docker del-port {bridge} {iface} {container_name}".split(),
            check=False,
            capture_output=False,
        )

    try:
        subprocess.run(cmd.split(), check=True)
        logging.info(
            "Interface %s connected to bridge:%s added to container %s",
            iface,
            bridge,
            container_name,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to add iface {iface} from {bridge} to container {container_name}."
        ) from exc

    if not vlan:
        return
    try:
        subprocess.run(
            f"ovs-docker set-vlan {bridge} {iface} {container_name} " f"{vlan}".split(),
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to set VLAN ID {vlan} on iface {iface}"
            f" from {bridge} in container {container_name}."
        ) from exc

    if not trunk:
        return
    try:
        subprocess.run(
            f"ovs-docker set-trunk {bridge} {iface} {container_name} "
            f"{trunk}".split(),
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to set Trunk IDs {trunk} on iface {iface}"
            f" from {bridge} in container {container_name}."
        ) from exc


def main() -> None:
    """Runner function.

    :raises RuntimeError: If dependency check fail.
    """
    # Initial Check if docker socket is loaded.
    if not os.path.exists("/var/run/docker.sock"):
        logging.error("Need to mount Docker socket!!")
        exit(1)

    # Initial check if openvswitch module is loaded.
    lsmod_out = subprocess.run(["lsmod"], check=True, capture_output=True)
    try:
        subprocess.run(
            ["grep", "openvswitch"],
            check=True,
            input=lsmod_out.stdout,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        logging.error("Openvswitch kernel modules need to be mounted from host!!")
        raise RuntimeError("Kernel modules for Openvswitch not loaded") from exc

    config = json.loads(Path("config.json").read_text(encoding="UTF-8"))

    # Initialize all parent bridges
    for bridge, info in config["bridge"].items():
        init_ovs_bridge(bridge, info)

    # Attach containers to parent bridges based on config.json
    for container, iface_info in config["container"].items():
        for info in iface_info:
            add_iface_to_container(container, info)

    # Introduce a sleep since supervisor can't add interval between restarts.
    time.sleep(5)


if __name__ == "__main__":
    main()
