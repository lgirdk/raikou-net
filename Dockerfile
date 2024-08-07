FROM docker:27.0.3-dind-alpine3.20

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="alpine3.20-dind-27.0.3"

WORKDIR /root

COPY ./app app

# hadolint ignore=DL3018
RUN apk add -u --no-cache \
    openvswitch \
    kmod \
    bash \
    openrc \
    openssh \
    uuidgen \
    iproute2 \
    bridge-utils \
    supervisor && \
    \
    # Configure SSH key
    /usr/bin/ssh-keygen -t rsa -b 4096 -N '' -f /etc/ssh/ssh_host_rsa_key && \
    sed -i 's,#PermitRootLogin.*$,PermitRootLogin yes,1' /etc/ssh/sshd_config && \
    \
    # Create OVS database and pid file directory
    mkdir -pv /var/run/openvswitch/ && \
    mkdir -pv /var/log/openvswitch/ && \
    chmod +x app/init

# Add supervisord configuration file
COPY ./config/supervisord.conf /etc/supervisord.conf
COPY ./util/ovs-docker /usr/bin/ovs-docker
COPY ./util/lxbr-docker /usr/bin/lxbr-docker

ENV PYTHONPATH "${PYTHONPATH}:/root/app/"
ENV DEBUG no
ENV USE_LINUX_BRIDGE false

ENTRYPOINT [ "app/init" ]
