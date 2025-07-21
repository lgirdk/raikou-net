#!/bin/bash -xe

if [ "$LEGACY" == "no" ]; then
    isolate_docker_iface
fi


#if no DNS servers are specifified, defaults will be used
echo "nameserver ${DNS_IPv4:-"172.25.1.2"}" > /etc/resolv.conf
echo "nameserver ${DNS_IPv6:-"2001:dead:beef:2::2"}" >> /etc/resolv.conf

chmod +x /root/pjsua
chmod +x /sbin/dhclient-script

/usr/sbin/sshd -D
