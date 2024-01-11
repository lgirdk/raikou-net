FROM docker:24.0.6-dind-alpine3.18

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="alpine3.18-dind-ovs_2.17"

WORKDIR /root

COPY ./app app

RUN apk add -u --no-cache \
    openvswitch=2.17.8-r0 \
    bash=5.2.15-r5 \
    openrc=0.48-r0 \
    openssh=9.3_p2-r1 \
    uuidgen=2.38.1-r8 \
    iproute2=6.3.0-r0 \
    supervisor=4.2.5-r2 && \
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
