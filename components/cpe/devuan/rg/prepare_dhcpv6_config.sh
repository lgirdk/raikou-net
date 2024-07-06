#!/bin/sh

if [ -f /etc/device.properties ]; then
    . /etc/device.properties
fi

VENDOR_SPEC_FILE="/etc/dibbler/udhcpc.vendor_specific"
OPTION_FILE="/tmp/vendor_spec.txt"
DHCP_CONFIG_FILE="/etc/dibbler/client.conf"
DHCP_CONFIG_FILE_RFS="/etc/dibbler/client.conf-basic"
DHCP_CONFIG_FILE_TMP="/tmp/dibbler/client.conf"
#interface=$ARM_INTERFACE

ethWanMode=`syscfg get eth_wan_enabled`
DSLite_Enabled=`syscfg get dslite_enable`
#interface is $ARM_INTERFACE which comes from device.properties
#interface=erouter0 is now specified in client.conf-basic
#if [ "$interface" ] && [ -f /etc/dibbler/client_back.conf ];then
#    sed -i "s/RDK-ESTB-IF/${interface}/g" /etc/dibbler/client_back.conf
#fi


if [ -f $OPTION_FILE ]; then
    rm -rf $OPTION_FILE
fi

updateOptInfo()
{
    opt_val=$1
    subopt_num=$2
    subopt_len=`echo ${#opt_val}`
    subopt_len_h=`printf "%04x\n" $subopt_len`;
    subopt_val_h=`echo -n $opt_val | busybox hexdump -e '13/1 "%02x"'`
    echo -n $subopt_num$subopt_len_h$subopt_val_h >> $OPTION_FILE
    return
}

updateDUIDInfo()
{
    EnpNum=3561
    ProdClass=`dmcli eRT retv Device.DeviceInfo.ProductClass`
    MfrOUI=`dmcli eRT retv Device.DeviceInfo.ManufacturerOUI`
    SrNum=`dmcli eRT retv Device.DeviceInfo.X_LGI-COM_SerialNumber`
    Idntfr=`echo -n $MfrOUI-$ProdClass-$SrNum | busybox hexdump -e '13/1 "%02x"'`
    echo "duid-type duid-en $EnpNum 0x$Idntfr"
}

if [ "$DSLite_Enabled" = "1" ];then
    echo "        option aftr" >> $OPTION_FILE
fi

# Add Option: Vendor Class (16) with Enterprise ID: 3561 (0x0de9), vendor-class-data: dslforum.org (length 0x000c + 0x64736C666F72756D2E6F7267)
echo "        option 0016 hex 0x00000de9000c64736c666f72756d2e6f7267" >> $OPTION_FILE

if [ "$EROUTER_DHCP_OPTION_EMTA_ENABLED" = "true" ] && [ "$ethWanMode" = "true" ]; then
    echo -n "        option 0017 hex 0x00000de9000100060027087A087B" >> $OPTION_FILE
else
    echo -n "        option 0017 hex 0x00000de9" >> $OPTION_FILE
fi

# MVXREQ-3046 suboptions 11 12 13 and 17
subOptionNumber=11
for ppValues in MANUFACTURER_OUI SERIAL_NUMBER C_PRODUCT_ID S_PRODUCT_ID ; do
    subOptionVal=`getpp show $ppValues`
    suboptionSize=`echo -n "$subOptionVal"|wc -c`
    printf  "%04x" $subOptionNumber >> $OPTION_FILE
    printf  "%04x" $suboptionSize >> $OPTION_FILE
    for ((i=0;i<${#subOptionVal};i++));do printf %02X >> $OPTION_FILE  \'${subOptionVal:$i:1}; done
    subOptionNumber=$((subOptionNumber + 1))
    if [ "$subOptionNumber" -eq "14" ]
    then
        subOptionNumber=$((subOptionNumber+3))
    fi
done

if [ "$EROUTER_DHCP_OPTION_EMTA_ENABLED" = "true" ] && [ "$ethWanMode" = "true" ]; then
    echo -n "0027000107" >> $OPTION_FILE
fi

log_level=`syscfg get dibbler_log_level`

if [ -z "$log_level" ] || [ $log_level -lt 1 ]; then
    log_level=1
elif [ $log_level -gt 8 ]; then
    log_level=4
fi

if [ -f "$DHCP_CONFIG_FILE_TMP" ]; then
    rm -rf $DHCP_CONFIG_FILE_TMP
fi

echo "log-level $log_level" > $DHCP_CONFIG_FILE_TMP

updateDUIDInfo >> $DHCP_CONFIG_FILE_TMP
sed '$d' $DHCP_CONFIG_FILE_RFS >> $DHCP_CONFIG_FILE_TMP
cat $OPTION_FILE >> $DHCP_CONFIG_FILE_TMP
echo >> $DHCP_CONFIG_FILE_TMP
echo "}" >> $DHCP_CONFIG_FILE_TMP
