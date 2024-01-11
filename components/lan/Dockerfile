FROM ssh:1.9.2p1

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="container_utils_1.1.1"

ENV LEGACY=yes
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY ./resources/container_utils-1.1.1-py3-none-any.whl container_utils-1.1.1-py3-none-any.whl

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u5 \
    dante-server=1.4.2+dfsg-7+b8 \
    dnsutils=1:9.18.19-1~deb12u1 \
    ftp=20210827-4 \
    iperf=2.1.8+dfsg-1 \
    iperf3=3.12-1+deb12u1 \
    iproute2=6.1.0-3 \
    iptables=1.8.9-2 \
    iputils-ping=3:20221126-1 \
    isc-dhcp-client=4.4.3-P1-2 \
    iw=5.19-1 \
    lighttpd=1.4.69-1 \
    ndisc6=1.0.5-1+b2 \
    net-tools=2.10-0.1 \
    netcat-openbsd=1.219-1 \
    nmap=7.93+dfsg1-1 \
    ntpdate=1:4.2.8p15+dfsg-2~1.2.2+dfsg1-1+deb12u1 \
    procps=2:4.0.2-3 \
    psmisc=23.6-1 \
    tcpdump=4.99.3-1 \
    tftpd-hpa=5.2+20150808-1.4 \
    traceroute=1:2.1.2-1 \
    tshark=4.0.11-1~deb12u1 \
    miniupnpc=2.2.4-1+b1 \
    webfs=1.21+ds1-12+b1 \
    wget=1.21.3-1+b2 \
    wpasupplicant=2:2.10-12 \
    xinetd=1:2.3.15.3-1+b1 \
    xxd=2:9.0.1378-2 \
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
