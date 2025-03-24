FROM ssh:v1.2.0


ENV LEGACY="no"
# Install packages required for the following repositories.
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin"

# Adding ENV to allow generation of FRR configurations
# Support enabled only for RIP, SMCROUTE and ZEBRA
ENV FRR_AUTO_CONF=yes

# Add ENV to enable NAT on uplink
# Generally eth0 interface, when container is created with docker bridge.
ENV ENABLE_NAT_ON=eth0

WORKDIR /root

# Copy FRR Daemon configs
COPY ./resources/frr.conf .
COPY ./resources/staticd.conf .
COPY ./resources/init .

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    autoconf \
    automake \
    flex \
    bison \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    build-essential && \
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
    dnsutils \
    iproute2 \
    iptables \
    iputils-ping \
    isc-dhcp-relay \
    net-tools \
    frr \
    frr-pythontools \
    telnet \
    tcpdump \
    smcroute \
    traceroute && \
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
    git \
    autoconf \
    automake \
    flex \
    bison \
    curl \
    ca-certificates \
    gnupg \
    build-essential && \
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

EXPOSE 22


# Adding Default IFACE env variables
ENV CPE_MGMT=cpe,10.1.1.1/24,2001:dead:cafe:1::1/64
ENV CPE_DATA=v10,10.1.2.1/24,2001:dead:cafe:2::1/64
ENV CPE_VOICE=v21,10.1.3.1/24,2001:dead:cafe:3::1/64

ENV FRR_DAEMONS="zebra staticd"

# Specify v4 RELAY IP, v6 RELAY IP
# Leaving empty by default
ENV DHCP_RELAY=,

ENTRYPOINT [ "/root/init" ]
