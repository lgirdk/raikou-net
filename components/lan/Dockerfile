FROM ssh:v1.2.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="container_utils_1.1.1"

ENV LEGACY=yes
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY ./resources/container_utils-1.1.1-py3-none-any.whl container_utils-1.1.1-py3-none-any.whl

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dante-server \
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
    ntpdate \
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

COPY ./resources/configs/tftpd-hpa/tftpd-hpa.conf /etc/default/tftpd-hpa
COPY ./resources/dhclient-script /sbin/dhclient-script
COPY ./resources/dhclient.conf /etc/dhcp/dhclient.conf
COPY ./init /root/init

EXPOSE 80/tcp
EXPOSE 69/udp

CMD ["/bin/bash", "/root/init"]
