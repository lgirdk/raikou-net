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

ENV AFTR_EP=""
ENV AFTR_ACL=""

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
COPY ./resources/configs/aftr/aftr.conf /root/aftr/aftr.conf
COPY ./resources/configs/aftr/aftr-script /root/aftr/aftr-script

EXPOSE 69/udp
EXPOSE 80/tcp

CMD ["/bin/bash", "/root/init"]
