#!/bin/bash

if [ "$LEGACY" == "no" ]; then
    isolate_docker_iface
fi

#if no DNS servers are specifified, defaults will be used
echo "nameserver ${DNS_IPv4:-"172.25.1.2"}" > /etc/resolv.conf
echo "nameserver ${DNS_IPv6:-"2001:dead:beef:2::2"}" >> /etc/resolv.conf

cat > /etc/kamailio/kamctlrc << EOF
SIP_DOMAIN=sipcenter.boardfarm.com
DBENGINE=MYSQL
DBRWUSER="$KAM_DB_USER"
DBRWPW="$KAM_DB_PWD"
EOF

cat > /etc/default/kamailio << EOF
RUN_KAMAILIO=yes
USER=$KAM_SRV_USER
CFGFILE=/etc/kamailio/kamailio.cfg
EOF

service mariadb start
sed -i "s/table = 0/table = -1/" /etc/rtpengine/rtpengine.conf

sysctl net.ipv6.conf.lo.disable_ipv6=0
killall -9 rtpengine
rtpengine --listen-ng=localhost:2223 --log-stderr -m 2000 -M 60000  --interface=any

./db_creation.sh

sed -i "s/kam_listen_ipv4/udp:$KAM_LISTEN_IPv4:5060/" /etc/kamailio/kamailio.cfg
sed -i "s/kam_listen_ipv6/udp:[$KAM_LISTEN_IPv6]:5060/" /etc/kamailio/kamailio.cfg
sed -i "s/kam_listen_alias/$KAM_LISTEN_ALIAS/" /etc/kamailio/kamailio.cfg

service kamailio start

/usr/sbin/sshd -D
