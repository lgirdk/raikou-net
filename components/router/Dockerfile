FROM ssh:1.9.2p1

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="frr_9.0"

# Install packages required for the following repositories.
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin"

# Adding Default IFACE env variables
ENV CPE_MGMT=vl_eth1,10.1.1.1/24,2001:dead:cafe:1::1/64
ENV CPE_DATA=vl_eth2,10.1.2.1/24,2001:dead:cafe:2::1/64
ENV CPE_VOICE=vl_eth3,10.1.3.1/24,2001:dead:cafe:3::1/64
ENV MCAST_TARGET=vl_eth2

# Specify v4 RELAY IP, v6 RELAY IP
# Leaving empty by default
ENV DHCP_RELAY=,

WORKDIR /root

# Copy FRR Daemon configs
COPY ./resources/ripd.conf .
COPY ./resources/zebra.conf .
COPY ./resources/smcroute.conf .
COPY ./resources/staticd.conf .
COPY ./resources/pimd.conf .
COPY ./resources/init .

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.39.2-1.1 \
    autoconf=2.71-3 \
    automake=1:1.16.5-1.3 \
    flex=2.6.4-8.2 \
    bison=2:3.8.2+dfsg-1+b1 \
    curl=7.88.1-10+deb12u5 \
    ca-certificates=20230311 \
    gnupg=2.2.40-1.1 \
    lsb-release=12.0-1 \
    build-essential=12.9 && \
    \
    # Add FRR source list for JAMMY release
    curl -s https://deb.frrouting.org/frr/keys.gpg | tee \
    /usr/share/keyrings/frrouting.gpg > /dev/null && \
    \
    echo deb "[signed-by=/usr/share/keyrings/frrouting.gpg]" \
    https://deb.frrouting.org/frr "$(lsb_release -s -c)" frr-stable | tee \
    -a /etc/apt/sources.list.d/frr.list && \
    \
    apt-get update && apt-get install -y --no-install-recommends \
    dnsutils=1:9.18.24-1 \
    iproute2=6.1.0-3 \
    iptables=1.8.9-2 \
    iputils-ping=3:20221126-1 \
    isc-dhcp-relay=4.4.3-p1-2 \
    net-tools=2.10-0.1 \
    frr=9.1-0~deb12u1 \
    frr-pythontools=9.1-0~deb12u1 \
    telnet=0.17+2.4-2+deb12u1 \
    tcpdump=4.99.3-1 \
    smcroute=2.5.6-1 \
    traceroute=1:2.1.2-1 && \
    \
    ## Fix "the END problem" in Quagga vtysh
    echo VTYSH_PAGER=more >> /etc/environment && \
    ## Enable IPv6 and IPv4 forwarding
    echo "net.ipv4.conf.all.forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv4.conf.default.forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv4.conf.all.mc_forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv4.conf.default.mc_forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.all.forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.default.forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.all.disable_ipv6 = 0" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.default.disable_ipv6 = 0" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.default.accept_ra = 2" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.all.mc_forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.default.mc_forwarding = 1" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.all.accept_ra = 2" >> /etc/sysctl.conf && \
    echo "net.ipv4.conf.all.rp_filter = 0" >> /etc/sysctl.conf && \
    ## Enable vlan
    echo 8021q >> /etc/modules && \
    ldconfig && \
    ## Set Precedence to IPv4
    sed -i "s/#precedence ::ffff:0:0\/96  100/precedence ::ffff:0:0\/96  100/" /etc/gai.conf && \
    ## Purge Files
    apt-get purge -y \
    git=1:2.39.2-1.1 \
    autoconf=2.71-3 \
    automake=1:1.16.5-1.3 \
    flex=2.6.4-8.2 \
    bison=2:3.8.2+dfsg-1+b1 \
    curl=7.88.1-10+deb12u5 \
    ca-certificates=20230311 \
    gnupg=2.2.40-1.1 \
    lsb-release=12.0-1 \
    build-essential=12.9 && \
    apt-get -y autoremove && \
    # Clear Cache
    rm -rf /var/lib/apt/lists/* && \
    \
    # Permissions
    mv /root/ripd.conf /etc/frr/ripd.conf && \
    mv /root/zebra.conf /etc/frr/zebra.conf && \
    mv /root/pimd.conf /etc/frr/pimd.conf && \
    mv /root/smcroute.conf /etc/smcroute.conf && \
    mv /root/staticd.conf /etc/frr/staticd.conf && \
    chown -R frr /etc/frr && \
    chmod +x init && \
    echo "root:bigfoot1" | chpasswd

ENTRYPOINT [ "/root/init" ]
