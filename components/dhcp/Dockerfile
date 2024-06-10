FROM ssh:1.9.2p1

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="kea_dhcp_2.5.2"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install essential packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u5 \
    iproute2=6.1.0-3 \
    iptables=1.8.9-2 \
    iputils-ping=3:20221126-1 \
    net-tools=2.10-0.1 \
    netcat-openbsd=1.219-1 \
    procps=2:4.0.2-3 \
    psmisc=23.6-1 \
    tcpdump=4.99.3-1 \
    traceroute=1:2.1.2-1 \
    python3=3.11.2-6 \
    python3-uvicorn=0.17.6-1 \
    python3-fastapi=0.92.0-1 \
    python3-httpx=0.23.3-1 \
    tshark=4.0.11-1~deb12u1 && \
    mkdir -p /var/log/kea && \
    rm -rf /var/lib/apt/lists/* && \
    \
    # Install KEA debian package
    curl -1sLf 'https://dl.cloudsmith.io/public/isc/kea-2-5/setup.deb.sh'| bash && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    isc-kea-admin=2.5.2-isc20230926095551 \
    isc-kea-common=2.5.2-isc20230926095551 \
    isc-kea-ctrl-agent=2.5.2-isc20230926095551 \
    isc-kea-dhcp4=2.5.2-isc20230926095551  \
    isc-kea-dhcp6=2.5.2-isc20230926095551  \
    isc-kea-doc=2.5.2-isc20230926095551     \
    isc-kea-dhcp-ddns=2.5.2-isc20230926095551  && \
    rm /etc/apt/sources.list.d/isc-kea-2-5.list && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./resources/kea_api.py /root/kea_api.py
COPY ./resources/init /root/init
COPY ./resources/kea-ctrl-agent.conf /etc/kea/
COPY ./resources/kea-dhcp4.conf /etc/kea/
COPY ./resources/kea-dhcp6.conf /etc/kea/
COPY ./resources/keactrl.conf /etc/kea/
COPY ./resources/keactrl /usr/sbin/

ENV PATH "/sbin:/bin:/usr/sbin:/usr/bin"
ENV LEGACY=yes
ENV FAST_API=no

EXPOSE 8000

ENTRYPOINT [ "/root/init" ]
