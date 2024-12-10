"""API Schemas for Raikou-Net."""

from pydantic import BaseModel, Field, field_validator


# pylint: disable=E0213
class VlanBaseModel(BaseModel):
    """A base model for VLAN-related configurations.

    This model handles the validation of VLAN, native VLAN, and trunk VLANs.
    """

    vlan: str | None = Field(
        None,
        description="Optional VLAN as a numeric string between 1 and 4095",
        title="VLAN",
    )
    trunk: str | None = Field(
        None,
        description="Comma-separated VLAN trunk (e.g., '100,200')",
        title="Trunk VLAN",
    )
    native: str | None = Field(
        None,
        description="Native VLAN as a numeric string between 1 and 4095",
        title="Native VLAN",
    )

    @field_validator("vlan", "trunk", "native", mode="before")
    def validate_vlan_range(cls, value: str | None) -> str | None:
        """Validate the trunk and native VLAN id range.

        :param value: Trunk or native VLAN as a string
        :return: The validated value if valid, otherwise raises ValueError
        :raises ValueError: If trunk/native VLAN is out of range or not formatted correctly.
        """
        vlan_range_limit = 4095
        if value is None:
            return value
        # Split the trunk VLAN values by comma and validate
        for vlan in value.split(","):
            if not vlan.isdigit():
                msg = f"VLAN {vlan} should be a numeric string"
                raise ValueError(msg)
            vlan_int = int(vlan)
            if not 1 <= vlan_int <= vlan_range_limit:
                msg = f"VLAN {vlan} should be between 1 and 4095"
                raise ValueError(msg)
        return value


class IfaceInfo(VlanBaseModel):
    """Network Interface model used for both Linux and OVS bridges.

    This model represents the parent/virtual interface information that
    will be added to a bridge.
    """

    iface: str = Field(
        ...,
        description="The interface name to be used for the bridge",
        title="Interface Name",
    )
    vlan: str | None = Field(
        None, description="Optional VLAN for the parent interface", title="VLAN"
    )
    trunk: str | None = Field(
        None,
        description="Optional trunk VLAN for the parent interface",
        title="Trunk VLAN",
    )
    native: str | None = Field(
        None,
        description="Optional native VLAN for the parent interface",
        title="Native VLAN",
    )


class BridgeInfo(BaseModel):
    """Information about the bridge including network settings.

    This model contains network configuration for a bridge, including IP addresses, IP ranges,
    and parent interfaces that should be attached to the bridge.
    """

    ipaddress: str | None = Field(
        None, description="IPv4 address of the bridge", title="IPv4 Address"
    )
    ip6address: str | None = Field(
        None, description="IPv6 address of the bridge", title="IPv6 Address"
    )
    iprange: str | None = Field(
        None,
        description="Range of IPv4 addresses to be used by the bridge",
        title="IPv4 Range",
    )
    ip6range: str | None = Field(
        None,
        description="Range of IPv6 addresses to be used by the bridge",
        title="IPv6 Range",
    )
    parents: list[IfaceInfo] | None = Field(
        ...,
        description="List of parent interfaces to be attached to the bridge",
        title="Parent Interfaces",
    )


class ContainerInfo(VlanBaseModel):
    """Information about the container and its interfaces.

    This model represents interface settings like IP address, gateway, and VLAN configurations
    to be applied to a bridge or container interface.
    """

    iface: str = Field(
        ..., description="The interface name to be attached", title="Interface Name"
    )
    bridge: str = Field(
        None,
        description="Name of the bridge the container needs to be part of.",
        title="Bridge Name",
    )
    ipaddress: str | None = Field(
        None,
        description="IP address to be assigned to the interface",
        title="IPv4 Address",
    )
    ip6address: str | None = Field(
        None, description="IPv6 address of the container", title="IPv6 Address"
    )
    gateway: str | None = Field(
        None, description="IPv4 gateway for the interface", title="IPv4 Gateway"
    )
    gateway6: str | None = Field(
        None, description="IPv6 gateway for the interface", title="IPv6 Gateway"
    )
    macaddress: str | None = Field(
        None,
        description="MAC address to set for the container's interface",
        title="MAC Address",
    )


class VethPairInfo(BaseModel):
    """Information for creating a veth pair and attaching it to a bridge.

    This model provides the configuration needed to create a veth pair and attach it to a bridge,
    including any optional VLAN mapping.
    """

    on: str = Field(
        ...,
        description="The bridge to which the veth pair will be attached",
        title="Bridge Name",
    )
    map: str | None = Field(
        None,
        description="Optional mapping for VLAN translation (e.g., '2005:100')",
        title="VLAN Mapping",
    )
