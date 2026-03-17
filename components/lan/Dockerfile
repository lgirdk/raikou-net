FROM ssh:v2.0.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="container_utils_1.1.1"

ENV LEGACY="no"
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY ./resources/container_utils-1.1.1-py3-none-any.whl container_utils-1.1.1-py3-none-any.whl

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    arping \
    curl \
    microsocks \
    dnsutils \
    ftp \
    iperf \
    iperf3 \
    iproute2 \
    iptables \
    iputils-ping \
    isc-dhcp-client \
    iw \
    lighttpd \
    ndisc6 \
    net-tools \
    netcat-openbsd \
    nmap \
    ntpsec-ntpdate \
    procps \
    psmisc \
    tcpdump \
    tftpd-hpa \
    traceroute \
    tshark \
    miniupnpc \
    webfs \
    wget \
    wpasupplicant \
    xinetd \
    xxd \
    && rm -rf /var/lib/apt/lists/*  && \
    \
    # Create TFTP boot directory
    mkdir /tftpboot && \
    \
    # Clean TFTP/HTTP directories
    rm -rf /var/www/html && ln -s /tftpboot /var/www/html && \
    \
    # PIP install SCAPY!!
    pip install --no-cache-dir scapy==2.5.0 && \
    pip install --no-cache-dir ./container_utils-1.1.1-py3-none-any.whl && \
    rm -rf /tmp/* && \
    echo "set enable-bracketed-paste off" >> /etc/inputrc

# Defaults ship to .dist/ — init copies any missing entry into the live path,
# so compose mounts on /etc/default/tftpd-hpa, /sbin/dhclient-script or
# /etc/dhcp/dhclient.conf are true overrides.
COPY ./resources/configs/tftpd-hpa/tftpd-hpa.conf /etc/default.dist/tftpd-hpa
COPY ./resources/dhclient-script /sbin/dhclient-script.dist
COPY ./resources/dhclient.conf /etc/dhcp.dist/dhclient.conf
COPY ./init /root/init

EXPOSE 80/tcp
EXPOSE 69/udp

CMD ["/bin/bash", "/root/init"]
