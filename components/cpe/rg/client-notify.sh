#!/bin/bash

# author: Sly Midnight
# This script was tested on OpenBSD, but it is likely to work on other BSDs as well.

source /etc/utopia/service.d/log_env_var.sh
source /etc/utopia/service.d/log_capture_path.sh
LOGFILE=/var/lib/dibbler/client.sh-log

# uncomment this to get full list of available variables
set >> $LOGFILE
RESOLV_CONF="/etc/resolv.conf"
RESOLV_CONF_TMP="/tmp/resolv_tmp.conf"
R=""
SYSEVENT_SET_CMD=()

mta_dhcp_option_received=0
echo "-----------" >> $LOGFILE

# Handle prefix expire event
if [ "$PREFIX1" != "" ]; then
    if [ "$1" = "expire" ]; then
        sysevent batchset "dhcpv6_server-status=down" "zebra-restart="
        # Exiting here in case of 'expire' event, as CCSP doesn't handle delete event for prefix/address.
        exit 0
    else
        SYSEVENT_SET_CMD+=(dhcpv6_server-status=up)
    fi
fi

hex2string () {
    i=0
    while [ $i -lt ${#1} ];
    do
        echo -en "\x"${1:$i:2}
        let "i += 2"
    done
}

convertval()
{
    IP_MODE=$2
    LEN=$3
    # For ipv4 we need to convert value into decimal
    if [ "$IP_MODE" = "v4" ];then
        APPEND_TO_VAL="."
        hex=`echo $1 | sed "s/.\{$LEN\}/& /g"`
        for i in $hex ; do
            dec_val=`echo -en $((16#$i))`
            formatted_val="$formatted_val""$dec_val""$APPEND_TO_VAL"
        done
    else
        # Add : after 4 characters to get the ipv6 address
        formatted_val=`echo $1 | sed "s/.\{$LEN\}/&:/g"`
    fi
    echo "$formatted_val" | sed 's/.$//'

    #echo "${bkup::-1}"
}

parse_dhcp_option()
{
    dhcp_option_val=$1
    dhcp_option_val=`echo "${dhcp_option_val//:}"`

    # to count number of characters in suboption value in a dhcp option
    VAL=2

    OPTION_FORMAT=""
    IP_MODE=$2
    if [ "$IP_MODE" = "v4" ]; then
        LEN=2
    else
        LEN=4
    fi
    EQUAL="="
    PRINT_FROM_INDEX=$((LEN+1))
    while [ "$dhcp_option_val" != "" ] ; do
        SUBOPTION=`echo $dhcp_option_val | awk '{print substr ($0, 0, LEN)}' LEN=$LEN`

        dhcp_option_val=`echo "$dhcp_option_val" | awk '{print substr($0,CUR)}' CUR=$PRINT_FROM_INDEX`
        SUBOPTION_LENGTH=`echo $dhcp_option_val | awk '{print substr ($0, 0, LEN)}' LEN=$LEN`
        dhcp_option_val=`echo "$dhcp_option_val" | awk '{print substr($0,CUR)}' CUR=$PRINT_FROM_INDEX`
        SUBOPTION_LENGTH=`echo $((16#$SUBOPTION_LENGTH))`
        #SUBOPTION_LENGTH=`echo "ibase=16; $SUBOPTION_LENGTH" | bc`

        LENGTH=`echo $(($SUBOPTION_LENGTH * $VAL))`
        SUBOPTION_VALUE=`echo "$dhcp_option_val" | awk '{print substr ($0, 0, v1)}' v1=$LENGTH`
        #SUBOPTION_VALUE=`convertval $SUBOPTION_VALUE $IP_MODE $LEN`
        if [ "$OPTION_FORMAT" = "" ];then
            OPTION_FORMAT="$SUBOPTION""$EQUAL""$SUBOPTION_VALUE"
        else
            OPTION_FORMAT="$OPTION_FORMAT"" ""$SUBOPTION""$EQUAL""$SUBOPTION_VALUE"
        fi

        SUBOPTION_LENGTH=$((LENGTH+1))
        dhcp_option_val=`echo "$dhcp_option_val" | cut -c "$SUBOPTION_LENGTH"-`
    done

    echo "$OPTION_FORMAT"
}

RESOLV_CONF_override_needed=0

if [ "$OPTION_NEXT_HOP" != "" ]; then
    ip -6 route del default > /dev/null 2>&1
    ip -6 route add default via ${OPTION_NEXT_HOP} dev $IFACE
    echo "Added default route via ${OPTION_NEXT_HOP} on interface $IFACE/$IFINDEX" >> $LOGFILE
fi

if [ "$OPTION_NEXT_HOP_RTPREFIX" != "" ]; then
    NEXT_HOP=`echo ${OPTION_NEXT_HOP_RTPREFIX} | awk '{print $1}'`
    NETWORK=`echo ${OPTION_NEXT_HOP_RTPREFIX} | awk '{print $2}'`
    #LIFETIME=`echo ${OPTION_NEXT_HOP_RTPREFIX} | awk '{print $3}'`
    METRIC=`echo ${OPTION_NEXT_HOP_RTPREFIX} | awk '{print $4}'`

    if [ "$NETWORK" == "::/0" ]; then
        ip -6 route del default > /dev/null 2>&1
        ip -6 route add default via ${OPTION_NEXT_HOP} dev $IFACE
        echo "Added default route via  ${OPTION_NEXT_HOP} on interface $IFACE/$IFINDEX" >> $LOGFILE
    else
        ip -6 route add ${NETWORK} nexthop via ${NEXT_HOP} dev $IFACE weight ${METRIC}
        echo "Added nexthop to network ${NETWORK} via ${NEXT_HOP} on interface $IFACE/$IFINDEX, metric ${METRIC}" >> $LOGFILE
    fi
fi

if [ "$OPTION_RTPREFIX" != "" ]; then
    ONLINK=`echo ${OPTION_RTPREFIX} | awk '{print $1}'`
    METRIC=`echo ${OPTION_RTPREFIX} | awk '{print $3}'`
    ip -6 route add ${ONLINK} dev $IFACE onlink metric ${METRIC}
    echo "Added route to network ${ONLINK} on interface $IFACE/$IFINDEX onlink, metric ${METRIC}" >> $LOGFILE
fi

if [ "$ADDR1" != "" ]; then
    echo "Address ${ADDR1} (operation $1) to client $REMOTE_ADDR on inteface $IFACE/$IFINDEX" >> $LOGFILE
    SYSEVENT_SET_CMD+=(ipv6_${IFACE}_start_time=$(cut -d. -f1 /proc/uptime))
    SYSEVENT_SET_CMD+=(ipv6_${IFACE}_pref_lifetime=${ADDR1PREF})
    SYSEVENT_SET_CMD+=(ipv6-status=up)
    SYSEVENT_SET_CMD+=(wan6_ipaddr=${ADDR1})
    # SYSEVENT_SET_CMD+=(wan_service-status=started)
    service_routed route-set
else
    echo "Address received as NULL" >> $LOGFILE
    ADDR1="::"
    ADDR1PREF=0
    ADDR1VALID=0
fi
ADDR1T1=$((ADDR1PREF * 50 / 100))
ADDR1T2=$((ADDR1PREF * 80 / 100))

if [ "$SRV_OPTION31" != "" ]; then
    echo "Option Sntp Server  ${SRV_OPTION31} (operation $1) to client $REMOTE_ADDR on inteface $IFACE/$IFINDEX" >> $LOGFILE
    OLD_SRV_OPTION31=`sysevent get wan6_ntp_srv`
    if [ "$SRV_OPTION31" != "$OLD_SRV_OPTION31" ]; then
        SYSEVENT_SET_CMD+=(wan6_ntp_srv=$SRV_OPTION31)
        if [ -f /usr/ccsp/updateTimesyncdConf.sh ]; then
            /usr/ccsp/updateTimesyncdConf.sh
        else
            sed -i "/\<NTP\>/ s/$/ $SRV_OPTION31/" "/etc/systemd/timesyncd.conf"
        fi
    fi
fi

suboption=""
suboption_data=""
if [ "$SRV_OPTION17" != "" ]; then
    for j in $SRV_OPTION17; do
    suboption=`echo $j | cut -d = -f 1`
    suboption_data=`echo $j | cut -d = -f 2`
    echo "suboption  is $suboption" >>$CONSOLEFILE
    echo " suboption_data  is $suboption_data" >>$CONSOLEFILE
    case "$suboption" in
        "vendor")
        echo "Suboption vendor-id is $suboption_data in option $SRV_OPTION17" >> $LOGFILE
        SYSEVENT_SET_CMD+=(ipv6-vendor-id=$suboption_data)
        ;;
        "38")
        echo "Suboption TimeOffset is  $suboption_data in option $SRV_OPTION17" >> $LOGFILE
        SYSEVENT_SET_CMD+=(ipv6-timeoffset=$suboption_data)
        ;;
        "39")
         echo "Suboption IP Mode Preference is  $suboption_data in option $SRV_OPTION17"
         SYSEVENT_SET_CMD+=(wan6_ippref=$suboption_data)
            Mta_Ip_Pref=`sysevent get MTA_IP_PREF`
            if [ "$Mta_Ip_Pref" = "" ];then
                echo "Setting MTA_IP_PREF value to $suboption_data"
                SYSEVENT_SET_CMD+=(MTA_IP_PREF=$suboption_data)
                mta_dhcp_option_received=1
            else
                echo "Mta_Ip_Pref value is already set to $Mta_Ip_Pref"
            fi
        ;;
        "1")
        echo "OPT17 for CL_V6OPTION_ACS_SERVER is received: $suboption_data">> $CONSOLEFILE
        suboption_data=`echo $suboption_data| sed "s/://g"`
        echo "suboption_data is $suboption_data" >> $CONSOLEFILE
        ascii_url=$(hex2string $suboption_data)
        echo "DHCPv6_ACS_URL $ascii_url" >> /tmp/dhcp_acs_url
        sysevent set DHCPv6_ACS_URL "$ascii_url"
        echo "sysevent set of ascii_url::$ascii_url from DHCP OPT17" >> $CONSOLEFILE
        ;;
        "2")
        echo "Suboption provisioning code is $suboption_data in option $SRV_OPTION17" >> $LOGFILE
        suboption_data=`echo $suboption_data| sed "s/://g"`
        provisioningCode=$(hex2string $suboption_data)
        syscfg set tr_prov_code "$provisioningCode"
        ;;
        "3")
        echo "Suboption List of Embedded Components in eDOCSIS Device is $suboption_data in option $SRV_OPTION17" >> $LOGFILE
        SYSEVENT_SET_CMD+=(ipv6-embd-comp-in-device=$suboption_data)
        ;;
        "2170")
        echo "Suboption List of Embedded Components in eDOCSIS Device is $suboption_data in option $SRV_OPTION17"
                  parsed_value=""
                  parsed_value=`parse_dhcp_option $suboption_data v6`
                  echo "SUBOPT2170 parsed value is $parsed_value"

                  suboption=""
                  suboption_data=""
                  for val in $parsed_value; do

                        suboption=`echo $val | cut -d = -f 1`
                        suboption_data=`echo $val | cut -d = -f 2`
                        case "$suboption" in
                        "0001")
                                echo "Suboption is $suboption and value is $suboption_data"
                                mta_v4_primary=`sysevent get MTA_DHCPv4_PrimaryAddress`
                                if [ "$mta_v4_primary" = "" ] ;then
                                       echo "Setting MTA_DHCPv4_PrimaryAddress value as $suboption_data "
                                       SYSEVENT_SET_CMD+=(MTA_DHCPv4_PrimaryAddress=$suboption_data)
                                       mta_dhcp_option_received=1
                                fi
                        ;;
                        "0002")

                                echo "Suboption is $suboption and value is $suboption_data"
                                mta_v4_secondary=`sysevent get MTA_DHCPv4_SecondaryAddress`
                                if [ "$mta_v4_secondary" = "" ] ;then
                                        echo "Setting MTA_DHCPv4_SecondaryAddress value as $suboption_data "
                                        SYSEVENT_SET_CMD+=(MTA_DHCPv4_SecondaryAddress=$suboption_data)
                                       mta_dhcp_option_received=1
                                fi

                        ;;
                        esac

                   done
                   ;;
        "2171")
        echo "Suboption List of Embedded Components in eDOCSIS Device is $suboption_data in option $SRV_OPTION17"
                 parsed_value=""
                 parsed_value=`parse_dhcp_option $suboption_data v6`
                 echo "SUBOPT2171 parsed value is $parsed_value"

                  suboption=""
                  suboption_data=""
                  for val in $parsed_value; do

                        suboption=`echo $val | cut -d = -f 1`
                        suboption_data=`echo $val | cut -d = -f 2`
                        case "$suboption" in
                        "0001")
                                echo "Suboption is $suboption and value is $suboption_data"
                                mta_v4_primary=`sysevent get MTA_DHCPv6_PrimaryAddress`
                                if [ "$mta_v4_primary" = "" ] ;then
                                                 echo "Setting MTA_DHCPv6_PrimaryAddress value as $suboption_data "
                                                 SYSEVENT_SET_CMD+=(MTA_DHCPv6_PrimaryAddress=$suboption_data)
                                               mta_dhcp_option_received=1
                                fi
                        ;;
                        "0002")

                                echo "Suboption is $suboption and value is $suboption_data"
                                mta_v4_secondary=`sysevent get MTA_DHCPv6_SecondaryAddress`
                                if [ "$mta_v4_secondary" = "" ] ;then
                                        echo "Setting MTA_DHCPv6_SecondaryAddress value as $suboption_data "
                                        SYSEVENT_SET_CMD+=(MTA_DHCPv6_SecondaryAddress=$suboption_data)
                                               mta_dhcp_option_received=1
                                fi

                        ;;
                       esac

                   done
        ;;

        esac
    done
fi

if [ "$mta_dhcp_option_received" -eq 1 ]; then
    echo "Setting dhcp_mta_option event as received"
    SYSEVENT_SET_CMD+=(dhcp_mta_option=received)
    mta_dhcp_option_received=0
fi

if [ "$SRV_OPTION23" != "" ] && [ "$SRV_OPTION23" != ":: " ]; then
    cp $RESOLV_CONF $RESOLV_CONF_TMP
    echo "comapring old and new dns IPV6 configuration " >> $CONSOLEFILE
    RESOLV_CONF_override_needed=0
    for i in $SRV_OPTION23; do
        new_ipv6_dns_server="nameserver $i"
        dns_matched=`grep "$new_ipv6_dns_server" "$RESOLV_CONF_TMP"`
        if [ "$dns_matched" = "" ]; then
            echo "$new_ipv6_dns_server is not present in old dns config so resolv_conf file overide is required " >> $CONSOLEFILE
            RESOLV_CONF_override_needed=1
            break
        fi
     done

   if [ "$RESOLV_CONF_override_needed" -eq 1 ]; then
     dns=`sysevent get wan6_ns`
     if [ "$dns" != "" ]; then
        echo "Removing old DNS IPV6 SERVER configuration from resolv.conf " >> $CONSOLEFILE
        for i in $dns; do
            dns_server="nameserver $i"
            sed -i "/$dns_server/d" "$RESOLV_CONF_TMP"
        done
     fi
        for i in $SRV_OPTION23; do
         R="${R}nameserver $i
"
        done

        echo -n "$R" >> "$RESOLV_CONF_TMP"
        echo "Adding new IPV6 DNS SERVER to resolv.conf " >> $CONSOLEFILE
        N=""
        while read line; do
        N="${N}$line
"
        done < $RESOLV_CONF_TMP

        echo -n "$N" > "$RESOLV_CONF"

        if [ -f /tmp/ipv6_renew_dnsserver_restart ]; then
            echo "After renew change in IPV6 dns config so restarting dhcp-server(dnsmasq) " >> $CONSOLEFILE
            SYSEVENT_SET_CMD+=(dhcp_server-stop=)
            SYSEVENT_SET_CMD+=(dhcp_server-start=)
        fi
        touch /tmp/ipv6_renew_dnsserver_restart
   else

        echo "old and new IPV6 dns config are same no resolv_conf file override required " >> $CONSOLEFILE
   fi
       rm -rf $RESOLV_CONF_TMP

   #Remove old IPv6 DNS list
   for i in $(sysevent get wan6_ns); do
       ip -6 rule del to $i lookup erouter
   done

   #Add new DNS list as received in DHCPv6 option-23
   for i in $SRV_OPTION23; do
       ip -6 rule add to $i lookup erouter
   done

     SYSEVENT_SET_CMD+=(wan6_ns=$SRV_OPTION23)
     SYSEVENT_SET_CMD+=(ipv6_nameserver=$SRV_OPTION23)
     dns=$SRV_OPTION23
fi

if [ "$SRV_OPTION24" != "" ]; then
    SYSEVENT_SET_CMD+=(wan6_domain=$SRV_OPTION24)
    SYSEVENT_SET_CMD+=(ipv6_dnssl=$SRV_OPTION24)
fi

if [ "$SRV_OPTION64" != "" ]; then
    SYSEVENT_SET_CMD+=(dslite_dhcpv6_endpointname=$SRV_OPTION64)
    SYSEVENT_SET_CMD+=(dslite_option64-status=received)
    echo "DHCP DS-Lite Option 64 received value: $SRV_OPTION64" >> $LOGFILE
else
    SYSEVENT_SET_CMD+=(dslite_dhcpv6_endpointname=)
    SYSEVENT_SET_CMD+=(dslite_option64-status="not received")
    echo "DHCP DS-Lite Option 64 not received" >> $LOGFILE
fi

parse_fqdn() {
    IFS=: read -a optionbytes
    local nbytes=${#optionbytes[@]}
    [ $nbytes -lt 4 ] && return 1
    local totlen=$((0x${optionbytes[2]} * 256 + 0x${optionbytes[3]}))
    [ "$((totlen+4))" -ne "$nbytes" ] && return 1

    local offset=4
    while [ $offset -lt $nbytes ]; do
        local wbytes=0x${optionbytes[offset]}
        [ $((wbytes)) -eq 0 ] && return 0
        [ $((offset+wbytes)) -ge $nbytes ] && return 1
        [ $offset -ne 4 ] && echo -ne .
        for ((i=1; i<=wbytes; i++)); do
            echo -ne "\x"${optionbytes[offset+i]}
        done
        offset=$((offset+wbytes+1))
    done
    return 0
}

# Option 56 suboption 1 is NTP server IPv6 address ( NTP_SUBOPTION_SRV_ADDR )
# Option 56 suboption 3 is NTP server FQDN ( NTP_SUBOPTION_SRV_FQDN )
#                                       Suboption 1 format
#             2 bytes                           2 bytes                     16 bytes
#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-++-+-+-+-+-+-+-+-+-+-+-+-+-+
#  |    NTP_SUBOPTION_MC_ADDR      |        suboption-len = N      |   NTP_SUBOPTION_SRV_ADDR |
#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-++-+-+-+-+-+-+-+-+-+-+-+-+-+
if [ "$SRV_OPTION56" != "" ]; then
    ntpv6_server=""
    suboption=$(echo "$SRV_OPTION56" | cut -d : -f2)
    if [ $suboption = "03" ]; then
        ntpv6_server=$(echo $SRV_OPTION56 | parse_fqdn)
        if [ $? -ne 0 ]; then
            echo "Failed to Pharse ntp FQDN" >> $LOGFILE
            ntpv6_server=""
        fi
    else
        ntpv6_server=$(echo "$SRV_OPTION56" | cut -d : -f5- | sed 's/://g;s/..../&:/g;s/:$//')
    fi
    old_ntpv6=`sysevent get dhcpv6_ntp_server`
    if [ "$ntpv6_server" != "$old_ntpv6" ]; then
        SYSEVENT_SET_CMD+=(dhcpv6_ntp_server=$ntpv6_server)
    fi
fi

if [ "$PREFIX1" != "" ]; then
    echo "Prefix ${PREFIX1} (operation $1) to client $REMOTE_ADDR on inteface $IFACE/$IFINDEX" >> $LOGFILE

    PREV_PREFIX=`sysevent get wan6_prefix`
    PREV_PREFIXLEN=`sysevent get wan6_prefixlen`
    if [ "$PREV_PREFIX" != "$PREFIX1" ]; then
        ip -6 addr del ${PREV_PREFIX}1/${PREV_PREFIXLEN} dev brlan0
    fi

    SYSEVENT_SET_CMD+=(wan6_prefix=$PREFIX1)
    SYSEVENT_SET_CMD+=(wan6_prefixlen=$PREFIX1LEN)
   # ip -6 addr add ${PREFIX1}1/${PREFIX1LEN} dev brlan0
else
    echo "Prefix received as NULL" >> $LOGFILE
    PREFIX1="::"
    PREFIX1PREF=0
    PREFIX1VALID=0
    PREFIX1LEN=0
fi
PREFIX1T1=$((PREFIX1PREF * 50 / 100))
PREFIX1T2=$((PREFIX1PREF * 80 / 100))

PREV_ADDR=$(sysevent get wan6_ipaddr)

if [ "$ADDR1" != "" ]; then
    service_routed route-set
fi

if [ -f /tmp/.ipv6dnsserver ]; then
    for i in $dns; do
        result=`grep $i /tmp/.ipv6dnsserver`
        if [ "$result" == "" ];then
            utc_time=`date -u`
            uptime=$(cut -d. -f1 /proc/uptime)
            echo "$utc_time DNS_server_IP_changed:$uptime" >> $CONSOLEFILE
            echo $dns > /tmp/.ipv6dnsserver
        fi
    done
else
    echo $dns > /tmp/.ipv6dnsserver
fi



#if [ -f /usr/ccsp/updateResolvConf.sh ]; then
#    /usr/ccsp/updateResolvConf.sh
#fi

# service_ipv6 can directly parse prefix, lease time, etc info from this file
echo "dibbler-client add ${ADDR1} 1 ${ADDR1T1} ${ADDR1T2} ${ADDR1PREF} ${ADDR1VALID} ${PREFIX1} ${PREFIX1LEN} 1 ${PREFIX1T1} ${PREFIX1T2} ${PREFIX1PREF} ${PREFIX1VALID} " > /tmp/ipv6_provisioned.config

SYSEVENT_SET_CMD+=(ipv6_prefix=$PREFIX1/$PREFIX1LEN)

sysevent batchset "${SYSEVENT_SET_CMD[@]}"

# Send notification to CCSP PAM
# RDK-B has not defined HAL for Ipv6 yet so this is a means to notify
echo "dibbler-client add ${ADDR1} 1 ${ADDR1T1} ${ADDR1T2} ${ADDR1PREF} ${ADDR1VALID} ${PREFIX1} ${PREFIX1LEN} 1 ${PREFIX1T1} ${PREFIX1T2} ${PREFIX1PREF} ${PREFIX1VALID} " >> /tmp/ccsp_common_fifo

if [ -n "$PREV_ADDR" ]; then
    ip -6 rule del from $PREV_ADDR lookup all_lans
    ip -6 rule del from $PREV_ADDR lookup erouter
fi
if [ -n "$ADDR1" ]; then
    ip -6 rule add from $ADDR1 lookup erouter
    ip -6 rule add from $ADDR1 lookup all_lans
fi

# sample return code. Dibbler will just print it out.
exit 3
