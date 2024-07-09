FROM ghcr.io/kamailio/kamailio:5.7.1-bullseye

LABEL maintainer="saurav.kochar01@infosys.com"
LABEL kamailio-version="5.7.1"
LABEL rtp-version="3.0.1"

ENV TIMEOUT="60"
ENV LEGACY="no"
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
COPY ./utils/isolate_docker_iface /usr/bin/isolate_docker_iface

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /root/

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    mariadb-server \
    net-tools \
    traceroute \
    dnsutils \
    sngrep \
    tcpdump \
    tshark \
    git \
    build-essential \
    openssh-server \
    && echo 'root:bigfoot1' | chpasswd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*Gateway Ports.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config \
    && mkdir /var/run/sshd \
    && chmod +x /root/init.sh \
    && chmod +x /root/db_creation.sh \
    && rm -rf /var/lib/apt/lists/* \
    && git clone -b v3.0.1 https://github.com/sippy/rtpproxy.git \
    && git -C rtpproxy submodule update --init --recursive

WORKDIR /root/rtpproxy/

RUN ./configure --disable-dependency-tracking \
    && make \
    && make install \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get remove -y git \
    build-essential

WORKDIR /root/

ENTRYPOINT [ "/root/init.sh" ]

# Expose SIP and RTP ports
EXPOSE 5060/udp
EXPOSE 7722/udp
EXPOSE 7723/udp
