#!/bin/sh

VOIP_WAN_ENABLED=`syscfg get voip_wan_enabled`
MANAGEMENT_WAN_ENABLED=`syscfg get management_wan_enabled`
VENDOR_CLASS_ID="eRouter1.0 dslforum.org"

dhcpv4_stop ()
{
    if [ -f /tmp/udhcpc.mg0.pid ]; then
    MANAGEMENT_PID=`cat /tmp/udhcpc.mg0.pid`
    echo "management pid ${MANAGEMENT_PID}"
    kill ${MANAGEMENT_PID}
    IP_ADDR=`sysevent get ipv4_mg0_ipaddr`
    if [ ! -z "$IP_ADDR" ]; then
        ip rule del from ${IP_ADDR} table 100
    fi
        sysevent set ipv4_mg0_ipaddr
        sysevent set ipv4_mg0_dns_0
        sysevent set ipv4_mg0_dns_1
        sysevent set ipv4_mg0_state down
        ip -4 addr flush dev mg0
    fi
    if [ -f /tmp/udhcpc.voip0.pid ]; then
        VOIP_PID=`cat /tmp/udhcpc.voip0.pid`
        echo "voip pid ${VOIP_PID}"
        kill ${VOIP_PID}
        IP_ADDR=`sysevent get ipv4_voip0_ipaddr`
        if [ ! -z "$IP_ADDR" ]; then
            ip rule del from ${IP_ADDR} table 200
        fi
        sysevent set ipv4_voip0_ipaddr
        sysevent set ipv4_voip0_dns_0
        sysevent set ipv4_voip0_dns_1
        sysevent set ipv4_voip0_state down
        ip -4 addr flush dev voip0
    fi
}

subopt_to_hex()
{
    subopt_val=$1
    subopt=$2
    subopt_len=`echo ${#subopt_val}`

    subopt_hex=`printf "%02x%02x" $subopt $subopt_len`
    for ((i=0; i<$subopt_len; i++)) do
        subopt_hex+=`printf "%02x" "'${subopt_val:$i:1}"`
    done
    echo -n $subopt_hex
}

get_option_43()
{
    suboptions=("EROUTER" "EROUTER" "EROUTER:EDVA")
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.SerialNumber`)
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.HardwareVersion`)
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.SoftwareVersion`)
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.X_CISCO_COM_BootloaderVersion`)
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.ManufacturerOUI`)
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.ModelNumber`)
    suboptions+=(`dmcli eRT retv Device.DeviceInfo.Manufacturer`)
    option_43=''
    for i in ${!suboptions[@]}; do
        option_43+=`subopt_to_hex ${suboptions[$i]} $(($i+1))`
    done
    option_43+=`subopt_to_hex EROUTER 15`
    echo $option_43
}

dhcpv4_start ()
{
    dhcpv4_stop
    if [ "${MANAGEMENT_WAN_ENABLED}" == "1" ]; then
        SEND_OPTION43=`get_option_43`
        ##/sbin/udhcpc -b -i mg0 -p /tmp/udhcpc.mg0.pid -s /etc/udhcpc_vlan.script -V "$VENDOR_CLASS_ID" -Y -x 43:$SEND_OPTION43
        /sbin/udhcpc -b -i mg0 -p /tmp/udhcpc.mg0.pid -s /etc/udhcpc_vlan.script -V "$VENDOR_CLASS_ID" -x 43:$SEND_OPTION43
    fi
    if [ "${VOIP_WAN_ENABLED}" == "1" ]; then
        /sbin/udhcpc -b -i voip0 -p /tmp/udhcpc.voip0.pid -s /etc/udhcpc_vlan.script
    fi
}

case "$1" in
    "dhcpv4_start")
    dhcpv4_start
    ;;
    "dhcpv4_stop")
    dhcpv4_stop
    ;;
esac
