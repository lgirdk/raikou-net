#!/bin/sh
#######################################################################
#   Copyright [2015] [ARRIS Corporation]
#
#   Licensed under the Apache License, Version 2.0 (the \"License\");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an \"AS IS\" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#######################################################################

if [ -f /etc/device.properties ];then
. /etc/device.properties
fi

if [ ! -d /var/log/dibbler ]; then
    mkdir -p /var/log/dibbler
fi

## Function: removeIfNotLink
removeIfNotLink()
{
    if [ ! -h $1 ] ; then
        echo "Removing $1"
        rm -rf $1
    fi
}

echo "TLV_IP_MODE: IPv6 Mode..!"

removeIfNotLink /var/lib/dibbler
rm -f /tmp/dibbler

mkdir -p /var/lib/dibbler
#/var/lib/dibbler is dibbler's default workdir
#but service_dhcpv6_client.sh looks vor client.pid in /tmp/dibbler
ln -s  /var/lib/dibbler /tmp/dibbler
touch /var/lib/dibbler/client.sh-log
#client-notify can be read-only -> "script /etc/dibbler/client-notify.sh" in client.conf
#cp /etc/dibbler/client-notify.sh /var/lib/dibbler/

if [ ! -d /var/log/dibbler ]; then
    mkdir -p /var/log/dibbler
fi

echo > /tmp/dibbler/radvd.conf
#QMxxx root only to avoid radvd insecure file permission
chmod 600 /tmp/dibbler/radvd.conf
echo > /tmp/dibbler/radvd.conf.old

#server.conf is linked to /var/tmp/dhcp6s.conf by commoncomponents for now
#echo > /tmp/dibbler/server.conf
#ln -s /tmp/dibbler/server.conf /etc/dibbler/server.conf

#Preparing Configuration for dibbler client
if [ -f /lib/rdk/prepare_dhcpv6_config.sh ]; then
    /lib/rdk/prepare_dhcpv6_config.sh
fi

exit 0
