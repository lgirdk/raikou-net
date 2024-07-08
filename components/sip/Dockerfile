FROM ghcr.io/kamailio/kamailio:5.7.1-bullseye

LABEL maintainer="saurav.kochar01@infosys.com"
LABEL kamailio-version="5.7.1"
LABEL rtp-version="3.0.1"

ENV DEBIAN_FRONTEND=noninteractive
ENV KAM_LISTEN_IPv4=""
ENV KAM_LISTEN_IPv6=""
ENV KAM_LISTEN_ALIAS=""
ENV KAM_SRV_USER="kamailio"
ENV KAM_DB_USER="kamailio"
ENV KAM_DB_PWD="test"
ENV KAM_DB_CHARSET="latin1"
ENV DNS_IPv4=""
ENV DNS_IPv6=""

COPY ./utils/init.sh /root/init.sh
COPY ./utils/kamailio_default.cfg /etc/kamailio/kamailio.cfg
COPY ./utils/db_creation.sh /root/db_creation.sh

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /root/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping=3:20210202-1 \
    mariadb-server=1:10.5.23-0+deb11u1 \
    net-tools=1.60+git20181103.0eebece-1 \
    traceroute=1:2.1.0-2+deb11u1 \
    dnsutils=1:9.16.48-1 \
    sngrep=1.4.8-1 \
    tcpdump=4.99.0-2+deb11u1 \
    tshark=3.4.10-0+deb11u1 \
    git=1:2.30.2-1+deb11u2 \
    build-essential=12.9 \
    openssh-server=1:8.4p1-5+deb11u3 \
    && echo 'root:bigfoot1' | chpasswd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*Gateway Ports.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config \
    && mkdir /var/run/sshd \
    && chmod +x /root/init.sh \
    && chmod +x /root/db_creation.sh \
    && git clone -b v3.0.1 https://github.com/sippy/rtpproxy.git \
    && git -C rtpproxy submodule update --init --recursive \
    && ./rtpproxy/configure --disable-dependency-tracking \
    && make \
    && make install \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get remove -y git \
    build-essential

ENTRYPOINT [ "/root/init.sh" ]

# Expose SIP and RTP ports
EXPOSE 5060
EXPOSE 7722
EXPOSE 7723
