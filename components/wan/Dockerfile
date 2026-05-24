# AFTR package build stage.
FROM debian:bookworm-slim AS builder

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
# AFTR uses pre-C99 `inline` semantics in jhash; force gnu89 inline so newer
# gcc (12+, bookworm/trixie) keeps emitting the out-of-line symbols.
RUN ./configure && make CFLAGS="-g -O2 -fgnu89-inline"


# DEBIAN WAN Image start from here.
FROM ssh:v2.0.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="lwds_lite_1.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV DNS_UPSTREAM=8.8.8.8
ENV STATIC_ROUTES=""
ENV AFTR_EP=""
ENV AFTR_ACL=""
ENV LEGACY="no"

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    microsocks \
    dnsmasq \
    dnsutils \
    hping3\
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

# Copy AFTR binary tree from build stage and ship default configs to .dist/.
# init seeds the live paths from .dist/ only when no override is mounted, so
# a compose `volumes:` entry can replace any of these files cleanly.
COPY --from=builder /root/aftr /root/aftr
COPY ./resources/configs/tftpd-hpa/tftpd-hpa.conf /etc/default.dist/tftpd-hpa
COPY ./init /root/init
COPY ./resources/configs/aftr/aftr.conf /root/aftr.dist/aftr.conf
COPY ./resources/configs/aftr/aftr-script /root/aftr.dist/aftr-script

EXPOSE 69/udp
EXPOSE 80/tcp

CMD ["/bin/bash", "/root/init"]
