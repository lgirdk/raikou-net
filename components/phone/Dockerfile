FROM debian:stable-slim

LABEL maintainer="saurav.kochar01@infosys.com"
LABEL pjsip-version="2.14"

ENV TIMEOUT="60"
ENV LEGACY="no"
ENV DEBIAN_FRONTEND=noninteractive
ENV DNS_IPv4=""
ENV DNS_IPv6=""

COPY ./utils/init.sh /root/init.sh
COPY ./utils/isolate_docker_iface /usr/bin/isolate_docker_iface

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
WORKDIR /root/

# hadolint ignore=DL3008, DL3009
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    iproute2 \
    openssh-server \
    isc-dhcp-client \
    git \
    iputils-ping \
    net-tools\
    traceroute \
    dnsutils\
    --reinstall ca-certificates \
    && echo 'root:bigfoot1' | chpasswd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*Gateway Ports.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config \
    && mkdir /var/run/sshd \
    && chmod +x /root/init.sh \
    && git clone -b 2.14 https://github.com/pjsip/pjproject.git

WORKDIR /root/pjproject/

RUN echo "#define PJ_HAS_IPV6 1" > ./pjlib/include/pj/config_site.h \
    && ./configure \
    && make dep \
    && make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get remove -y git \
    build-essential

WORKDIR /root/

COPY ./resources/dhclient-script /sbin/dhclient-script
COPY ./resources/dhclient.conf /etc/dhcp/dhclient.conf

CMD [ "/root/init.sh" ]
