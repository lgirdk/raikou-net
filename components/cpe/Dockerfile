FROM dyne/devuan:beowulf as BUILD

WORKDIR /root
COPY service_udhcpc service_udhcpc
COPY wanmgr_ipc wanmgr_ipc

ENV DEBIAN_FRONTEND=noninteractive


# hadolint ignore=DL3008
RUN apt-get --allow-releaseinfo-change update && apt-get install -y --no-install-recommends \
    build-essential \
    nanomsg-utils \
    libnanomsg-dev

WORKDIR /root/service_udhcpc
RUN sh build.sh
WORKDIR /root/wanmgr_ipc
RUN sh build.sh

FROM dyne/devuan:beowulf

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="devuan-beowulf"

# COPY custom image artifacts first
COPY ./.bashrc /root/.bashrc
COPY ./interfaces /etc/network/interfaces

# COPY RG Artifacts
COPY ./rg/rg.start /etc/boot.d/start
COPY ./rg/device.properties /etc/
COPY ./rg/syscfg /usr/bin/
COPY ./rg/sysevent /usr/bin/
COPY ./rg/dmcli /usr/bin/
COPY ./rg/getpp /usr/bin/
COPY ./rg/scratchpadctl /usr/bin/
COPY --from=BUILD /root/service_udhcpc/service_udhcpc /usr/bin
COPY --from=BUILD /root/wanmgr_ipc/wanmgr_ipc /usr/bin
COPY ./rg/wanmgr_ipc_user_script.sh /etc/
COPY ./rg/wanmgr_pipe /usr/bin
COPY ./rg/udhcpc_vlan.script /etc/
COPY ./rg/vlan_dhcp_service.sh /root/
COPY ./rg/vlan_setup.sh /root/
COPY ./rg/dibbler-init.sh /lib/rdk/
COPY ./rg/prepare_dhcpv6_config.sh /lib/rdk/
COPY ./rg/dibbler-server-notify.sh /etc/dibbler/
COPY ./rg/client-notify.sh /etc/dibbler/
COPY ./rg/client.conf-basic /etc/dibbler/

ENV DEBIAN_FRONTEND=noninteractive
ENV EROUTER_VLAN 131
ENV MGMT_VLAN 121
ENV VOICE_VLAN 117

# hadolint ignore=DL3008,DL4005
RUN apt-get --allow-releaseinfo-change update && apt-get install -y --no-install-recommends \
    procps \
    tcpdump \
    iptables \
    strace \
    bridge-utils \
    iperf3 \
    netcat \
    socat \
    traceroute \
    vim \
    syslog-ng \
    psmisc \
    lsof \
    quagga \
    bind9 \
    nanomsg-utils \
    udhcpc \
    dhcpcd5 \
    isc-dhcp-server \
    dnsmasq \
    openresolv \
    ntp \
    radvd \
    dibbler-client \
    dibbler-server && \
    rm -rf /var/lib/apt/lists/* && \
    \
    # Removing /etc configurations
    rm /etc/init.d/isc-dhcp-server && \
    rm /etc/init.d/dnsmasq && \
    rm /etc/init.d/bind9 && \
    rm /etc/init.d/ntp && \
    rm /etc/init.d/radvd && \
    rm /etc/init.d/dibbler-server && \
    rm /etc/init.d/dibbler-client && \
    rm /etc/init.d/dhcpcd && \
    rm /bin/sh && \
    ln -s /bin/bash /bin/sh && \
    rm -rf /var/log/* && \
    \
    # Change file permissions
    chmod 755 /etc/boot.d/start && \
    chmod 755 /etc/wanmgr_ipc_user_script.sh && \
    chmod 755 /etc/udhcpc_vlan.script && \
    chmod 755 /root/vlan_dhcp_service.sh  && \
    chmod 755 /root/vlan_setup.sh && \
    chmod 755 /etc/dibbler/dibbler-server-notify.sh && \
    chmod 755 /etc/dibbler/client-notify.sh && \
    chmod -R 755 /usr/bin/ && \
    chmod -R 755 /lib/rdk && \
    # Dibble symlinks
    rm -rf /etc/dibbler/client.conf /etc/dibbler/server.conf && \
    rm -rf /etc/dibbler/server.conf && \
    ln -s /tmp/dibbler/client.conf /etc/dibbler/client.conf  && \
    ln -s /var/tmp/dhcp6s.conf /etc/dibbler/server.conf && \
    update-alternatives --set iptables /usr/sbin/iptables-legacy && \
    update-alternatives --set ip6tables /usr/sbin/ip6tables-nft
