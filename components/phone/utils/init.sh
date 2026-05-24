#!/bin/bash -xe

if [ "$LEGACY" == "no" ]; then
    isolate_docker_iface
fi

# Seed live dhclient config / script from baked defaults — compose mounts win.
mkdir -p /etc/dhcp
[ -f /etc/dhcp/dhclient.conf ] || cp /etc/dhcp.dist/dhclient.conf /etc/dhcp/dhclient.conf
[ -f /sbin/dhclient-script ]   || cp /sbin/dhclient-script.dist   /sbin/dhclient-script

#if no DNS servers are specifified, defaults will be used
echo "nameserver ${DNS_IPv4:-"172.25.1.2"}" > /etc/resolv.conf
echo "nameserver ${DNS_IPv6:-"2001:dead:beef:2::2"}" >> /etc/resolv.conf

chmod +x /root/pjsua
chmod +x /sbin/dhclient-script

/usr/sbin/sshd -D
