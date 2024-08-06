FROM ghcr.io/kamailio/kamailio:5.7.1-bullseye

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
ENV RTP_ENGINE_VER=""
ENV RTP_ENGINE_DATE=""

LABEL maintainer="saurav.kochar01@infosys.com"
LABEL version="5.7.1-bullseye"
LABEL rtpengine-version=${RTP_ENGINE_VER:-"13.0.0.0"}

COPY ./utils/init.sh /root/init.sh
COPY ./utils/db_creation.sh /root/db_creation.sh
COPY ./utils/isolate_docker_iface /usr/bin/isolate_docker_iface
COPY ./utils/kamailio_default.cfg /etc/kamailio/kamailio.cfg

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /root/

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    less \
    iputils-ping \
    mariadb-server \
    net-tools \
    traceroute \
    dnsutils \
    sngrep \
    tcpdump \
    tshark \
    git \
    openssh-server \
    debhelper-compat \
    default-libmysqlclient-dev \
    discount \
    gperf \
    libavcodec-dev \
    libavfilter-dev \
    libavformat-dev \
    libavutil-dev \
    libbcg729-dev \
    libbencode-perl \
    libcrypt-openssl-rsa-perl \
    libcrypt-rijndael-perl \
    libcurl4-openssl-dev  \
    libdigest-crc-perl \
    libdigest-hmac-perl \
    libevent-dev \
    libhiredis-dev \
    libio-multiplex-perl \
    libio-socket-inet6-perl \
    libiptc-dev \
    libjson-glib-dev \
    libjson-perl \
    libmnl-dev \
    libmosquitto-dev \
    libncurses-dev \
    libnet-interface-perl \
    libnftnl-dev \
    libopus-dev \
    libpcap0.8-dev \
    libsocket6-perl \
    libspandsp-dev \
    libswresample-dev \
    libsystemd-dev \
    libtest2-suite-perl \
    liburing-dev  \
    libwebsockets-dev \
    libxmlrpc-core-c3-dev \
    libxtables-dev  \
    iptables  \
    pandoc \
    pkgconf \
    python3-websockets \
    build-essential:native \
    dh-sequence-dkms \
    systemd \
    dkms \
    liburing-dev \
    && echo 'root:bigfoot1' | chpasswd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*Gateway Ports.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config \
    && mkdir /var/run/sshd \
    && chmod +x /root/init.sh \
    && chmod +x /root/db_creation.sh \
    && git clone https://github.com/sipwise/rtpengine.git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/rtpengine/

# hadolint ignore=SC2046
RUN git reset --hard $(git rev-list -1 $(git rev-parse --until=${RTP_ENGINE_DATE:-2024-08-05}) master) \
    && dpkg-buildpackage -d

WORKDIR /root/

RUN dpkg -i ngcp-rtpengine-kernel-dkms_13.0.0.0+0~mr13.0.0.0_all.deb \
    && dpkg -i ngcp-rtpengine-daemon_13.0.0.0+0~mr13.0.0.0_amd64.deb \
    && rm ngcp-rtpengine* \
    && apt-get remove -y git

ENTRYPOINT [ "/root/init.sh" ]

# Expose SIP and RTP ports
EXPOSE 5060/udp
EXPOSE 7722/udp
EXPOSE 7723/udp
