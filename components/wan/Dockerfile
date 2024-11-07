# AFTR package build stage.
FROM debian:buster-20220316-slim AS builder

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
ENV AFTR_PACKAGE_URL="https://downloads.isc.org/isc/lwds-lite/1.0/rt28354.tbz"
RUN wget -q $AFTR_PACKAGE_URL --no-check-certificate \
    && tar -xf rt28354.tbz && mv rt28354 aftr

WORKDIR /root/aftr
RUN ./configure && make


# DEBIAN WAN Image start from here.
FROM ssh:v1.2.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="lwds_lite_1.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV DNS_UPSTREAM=8.8.8.8

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dante-server \
    dnsmasq \
    dnsutils \
    iperf \
    iperf3 \
    iproute2 \
    iptables \
    iputils-ping \
    lighttpd \
    net-tools \
    netcat-openbsd \
    nmap \
    procps \
    psmisc \
    snmp \
    tcpdump \
    tftpd-hpa \
    traceroute \
    tshark \
    vsftpd \
    wget \
    xinetd \
    xxd \
    webfs \
    && rm -rf /var/lib/apt/lists/* && \
    pip --no-cache-dir install pysnmp==4.4.12 && \
    mkdir /tftpboot && \
    rm -rf /var/www/html && \
    ln -s /tftpboot /var/www/html

# Copy AFTR from build stage.
COPY --from=builder /root/aftr /root/aftr
COPY ./resources/configs/tftpd-hpa/tftpd-hpa.conf /etc/default/tftpd-hpa
COPY ./init /root/init

RUN printf '## section 0: global parameters\n defmtu 1420\n defmss on\n deftoobig off\n## section 1: required parameters\naddress endpoint\naddress icmp 198.18.200.111\npool 198.18.200.111 tcp 5000-59999\npool 198.18.200.111 udp 5000-59999\npcp 198.18.200.111 tcp 60000-64999\npcp 198.18.200.111 udp 60000-64999\n#All IPv6 ACLs\n' > /root/aftr/aftr.conf

RUN printf '#!/bin/sh \n aftr_start() \n {\n ip link set tun0 up \n sysctl -w net.ipv4.ip_forward=1\n sysctl -w net.ipv6.conf.all.forwarding=1\n sysctl -w net.ipv6.conf.all.disable_ipv6=0\n ip addr add 192.0.0.1 peer 192.0.0.2 dev tun0\n ip route add 198.18.0.0/16 dev tun0\n ip -6 route add \n iptables -t nat -F\n iptables -t nat -A POSTROUTING -s 198.18.200.111 -j SNAT --to-source $PUBLIC\n iptables -t nat -A PREROUTING -p tcp -d $PUBLIC --dport 60000:64999 -j DNAT --to-destination 198.18.200.111\n iptables -t nat -A PREROUTING -p udp -d $PUBLIC --dport 60000:64999 -j DNAT --to-destination 198.18.200.111\n iptables -t nat -A OUTPUT -p tcp -d $PUBLIC --dport 60000:64999 -j DNAT --to-destination 198.18.200.111\n iptables -t nat -A OUTPUT -p udp -d $PUBLIC --dport 60000:64999 -j DNAT --to-destination 198.18.200.111\n }\n aftr_stop()\n {\n iptables -t nat -F\n ip link set tun0 down\n }\n set -x\n PUBLIC=`ip addr show dev eth1 | grep -w inet | awk "{print $2}" | awk -F/ "{print $1}"`\n case "$1" in\n start)\n aftr_start\n ;;\n stop)\n aftr_stop\n ;;\n *)\n echo "Usage: $0 start|stop"\n exit 1\n ;;\n esac\n exit 0\n' > /root/aftr/aftr-script

EXPOSE 69/udp
EXPOSE 80/tcp

CMD ["/bin/bash", "/root/init"]
