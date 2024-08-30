#!/bin/bash -xe

if [ "$LEGACY" == "no" ]; then
    isolate_docker_iface
fi

mv /root/pjproject/pjsip-apps/bin/pjsua-x86_64-unknown-linux-gnu /root/pjproject/pjsip-apps/bin/pjsua

#if no DNS servers are specifified, defaults will be used
echo "nameserver ${DNS_IPv4:-"172.25.1.2"}" > /etc/resolv.conf
echo "nameserver ${DNS_IPv6:-"2001:dead:beef:2::2"}" >> /etc/resolv.conf

chmod +x /sbin/dhclient-script

echo "export PATH=/root/pjproject/pjsip-apps/bin:$PATH" >> /root/.bashrc

/usr/sbin/sshd -D
