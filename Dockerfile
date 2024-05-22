FROM docker:25.0.4-dind-alpine3.19

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="alpine3.18-dind-ovs_2.17"

WORKDIR /root

COPY ./app app

RUN apk add -u --no-cache \
    openvswitch=2.17.9-r0 \
    kmod=31-r2 \
    bash=5.2.21-r0 \
    openrc=0.52.1-r2 \
    openssh=9.6_p1-r0 \
    uuidgen=2.39.3-r0 \
    iproute2=6.6.0-r0 \
    supervisor=4.2.5-r4 && \
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

ENV PYTHONPATH "${PYTHONPATH}:/root/app/"
ENV DEBUG no

ENTRYPOINT [ "app/init" ]
