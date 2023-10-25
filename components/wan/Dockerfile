# AFTR package build stage.
FROM debian:buster-20220316-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.6 \
    wget=1.20.1-1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
ENV AFTR_PACKAGE_URL="https://downloads.isc.org/isc/lwds-lite/1.0/rt28354.tbz"
RUN wget -q $AFTR_PACKAGE_URL --no-check-certificate \
    && tar -xf rt28354.tbz && mv rt28354 aftr

WORKDIR /root/aftr
RUN ./configure && make


# DEBIAN WAN Image start from here.
FROM ssh:1.9.2p1

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="lwds_lite_1.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV DNS_UPSTREAM=8.8.8.8

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u4 \
    dante-server=1.4.2+dfsg-7+b8 \
    dnsmasq=2.89-1 \
    dnsutils=1:9.18.19-1~deb12u1 \
    iperf=2.1.8+dfsg-1 \
    iperf3=3.12-1+deb12u1 \
    iproute2=6.1.0-3 \
    iptables=1.8.9-2 \
    iputils-ping=3:20221126-1 \
    lighttpd=1.4.69-1 \
    net-tools=2.10-0.1 \
    netcat-openbsd=1.219-1 \
    nmap=7.93+dfsg1-1 \
    procps=2:4.0.2-3 \
    psmisc=23.6-1 \
    snmp=5.9.3+dfsg-2 \
    tcpdump=4.99.3-1 \
    tftpd-hpa=5.2+20150808-1.4 \
    traceroute=1:2.1.2-1 \
    tshark=4.0.6-1~deb12u1 \
    vsftpd=3.0.3-13+b2 \
    wget=1.21.3-1+b2 \
    xinetd=1:2.3.15.3-1+b1 \
    xxd=2:9.0.1378-2 \
    webfs=1.21+ds1-12+b1 \
    && rm -rf /var/lib/apt/lists/* && \
    pip --no-cache-dir install pysnmp==4.4.12 && \
    mkdir /tftpboot && \
    rm -rf /var/www/html && \
    ln -s /tftpboot /var/www/html

# Copy AFTR from build stage.
COPY --from=builder /root/aftr /root/aftr
COPY ./resources/configs/tftpd-hpa/tftpd-hpa.conf /etc/default/tftpd-hpa
COPY ./init /root/init

EXPOSE 69/udp
EXPOSE 80/tcp

CMD ["/bin/bash", "/root/init"]
