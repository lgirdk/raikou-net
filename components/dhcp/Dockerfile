FROM ssh:v1.2.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="kea-2-6"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
# Install essential packages
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    iptables \
    iputils-ping \
    net-tools \
    netcat-openbsd \
    procps \
    psmisc \
    tcpdump \
    traceroute \
    python3 \
    python3-uvicorn \
    python3-fastapi \
    python3-httpx \
    tshark && \
    mkdir -p /var/log/kea && \
    rm -rf /var/lib/apt/lists/* && \
    \
    # Install KEA debian package
    curl -1sLf 'https://dl.cloudsmith.io/public/isc/kea-2-6/setup.deb.sh'| bash && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    isc-kea-admin \
    isc-kea-common \
    isc-kea-ctrl-agent \
    isc-kea-dhcp4 \
    isc-kea-dhcp6  \
    isc-kea-doc    \
    isc-kea-dhcp-ddns  && \
    rm /etc/apt/sources.list.d/isc-kea-2-6.list && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./resources/kea_api.py /root/kea_api.py
COPY ./resources/init /root/init
COPY ./resources/kea-ctrl-agent.conf /etc/kea/
COPY ./resources/kea-dhcp4.conf /etc/kea/
COPY ./resources/kea-dhcp6.conf /etc/kea/
COPY ./resources/keactrl.conf /etc/kea/
COPY ./resources/keactrl /usr/sbin/

ENV PATH "/sbin:/bin:/usr/sbin:/usr/bin"
ENV LEGACY="no"
ENV FAST_API=no

EXPOSE 8000

ENTRYPOINT [ "/root/init" ]
