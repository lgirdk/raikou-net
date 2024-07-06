FROM ssh:1.9.2p1

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="frr_9.0"

# Install packages required for the following repositories.
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin"

# Adding ENV to allow generation of FRR configurations
# Support enabled only for RIP, SMCROUTE and ZEBRA
ENV FRR_AUTO_CONF=yes

# Add ENV to enable NAT on uplink
# Generally eth0 interface, when container is created with docker bridge.
ENV ENABLE_NAT_ON=eth0

# Following ENV are only valid in case of AUTO_CONF=yes
# TRIPLE PLAY generates configuration for voice, management and data services.
# Each service should translate to one interface in Zebra
ENV TRIPLE_PLAY=yes

# If TRIPLE_PLAY is disabled, then only the DATA service is considered.
# Adding Default IFACE env variables for TRIPLE_PLAY=yes
ENV CPE_MGMT_IFACE=vl_eth1
ENV CPE_DATA_IFACE=vl_eth2
ENV CPE_VOICE_IFACE=vl_eth3

# IP bundles that need to be assigned to each service interface
# You can add more values by separating them with ';'
# Useful when TRIPLE_PLAY is disabled and only DATA interface is active.
ENV CPE_MGMT_BUNDLE=10.1.1.1/24,2001:dead:cafe:1::1/64
ENV CPE_DATA_BUNDLE=10.1.2.1/24,2001:dead:cafe:2::1/64
ENV CPE_VOICE_BUNDLE=10.1.3.1/24,2001:dead:cafe:3::1/64

ENV FRR_DAEMONS="zebra ripd pimd"

# Specify UPSTREAM IFACE,v4 RELAY IP,v6 RELAY IP
# Leaving empty by default
ENV DHCP_RELAY=

WORKDIR /root

# Copy FRR Daemon configs
COPY ./resources/frr.conf .
COPY ./resources/staticd.conf .
COPY ./resources/init .

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.39.2-1.1 \
    autoconf=2.71-3 \
    automake=1:1.16.5-1.3 \
    flex=2.6.4-8.2 \
    bison=2:3.8.2+dfsg-1+b1 \
    curl=7.88.1-10+deb12u6 \
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
    frr=10.0.1-0~deb12u1 \
    frr-pythontools=10.0.1-0~deb12u1 \
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
    curl=7.88.1-10+deb12u6 \
    ca-certificates=20230311 \
    gnupg=2.2.40-1.1 \
    lsb-release=12.0-1 \
    build-essential=12.9 && \
    apt-get -y autoremove && \
    # Clear Cache
    rm -rf /var/lib/apt/lists/* && \
    \
    # Permissions
    mv /root/frr.conf /etc/frr/frr.conf && \
    mv /root/staticd.conf /etc/frr/staticd.conf && \
    chown -R frr /etc/frr && \
    chmod +x init && \
    echo "root:bigfoot1" | chpasswd

ENTRYPOINT [ "/root/init" ]
