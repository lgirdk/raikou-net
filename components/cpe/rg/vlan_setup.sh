#!/bin/sh

VOIP_WAN_ENABLED=`syscfg get voip_wan_enabled`
MANAGEMENT_WAN_ENABLED=`syscfg get management_wan_enabled`
WAN_MAC=$(getpp show WAN_MAC_ADDRESS)

vlans_create ()
{
    if [ $(scratchpadctl dump RdpaWanType) == "GBE" ]; then
        BASE_INTERFACE="eth0"
    else
        BASE_INTERFACE="veip0"
    fi

    if [ "${MANAGEMENT_WAN_ENABLED}" == "1" ]; then
        MANAGEMENT_VLAN=`syscfg get management_vlan`
        if [ ${MANAGEMENT_VLAN} == "-1" ]; then
            ip link add link ${BASE_INTERFACE} mg0 type macvlan
        else
            ip link add link ${BASE_INTERFACE} name mg0 type vlan id ${MANAGEMENT_VLAN}
            MANAGEMENT_EGRESS_MAP=`syscfg get management_skb2vlan_priority_map`
            if [ ! -z "$MANAGEMENT_EGRESS_MAP" ]; then
                ip link set mg0 type vlan egress ${MANAGEMENT_EGRESS_MAP}
            fi
        fi
        MG0_MAC=$(sed -e 's/../&:/g' -e 's/:$//' <<< $(printf '%012x\n' $(echo $(( $(echo $(( 16#$WAN_MAC )))+5 )))))
        ip link set dev mg0 address $MG0_MAC
        ip link set mg0 up
        ip rule add oif mg0 table 100
        ip rule add iif mg0 table 100
        ip route add table 100 unreachable default metric 4278198272
    fi
    if [ "${VOIP_WAN_ENABLED}" == "1" ]; then
        VOIP_VLAN=`syscfg get voip_vlan`
        if [ ${VOIP_VLAN} == "-1" ]; then
            ip link add link ${BASE_INTERFACE} voip0 type macvlan
        else
            ip link add link ${BASE_INTERFACE} name voip0 type vlan id ${VOIP_VLAN}
            VOIP_EGRESS_MAP=`syscfg get voip_skb2vlan_priority_map`
            if [ ! -z "$VOIP_EGRESS_MAP" ]; then
                ip link set voip0 type vlan egress ${VOIP_EGRESS_MAP}
            fi
        fi
        VOIP0_MAC=$(sed -e 's/../&:/g' -e 's/:$//' <<< $(printf '%012x\n' $(echo $(( $(echo $(( 16#$WAN_MAC )))+4 )))))
        ip link set dev voip0 address $VOIP0_MAC
        ip link set voip0 up
        ip rule add oif voip0 table 200
        ip rule add iif voip0 table 200
        ip route add table 200 unreachable default metric 4278198272
    fi
}

vlans_delete ()
{
    ip link set mg0 down
    ip rule del oif mg0 table 100
    ip rule del iif mg0 table 100
    ip route flush table 100
    ip link del mg0
    ip link set voip0 down
    ip rule del oif voip0 table 200
    ip rule del iif voip0 table 200
    ip route flush table 200
    ip link del voip0
}

case "$1" in
    "create")
    vlans_create
    ;;
    "delete")
    vlans_delete
    ;;
esac
