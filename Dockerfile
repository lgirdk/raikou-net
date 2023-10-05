FROM docker:24.0.2-dind-alpine3.18

WORKDIR /root

RUN apk add -u --no-cache \
    openvswitch=2.17.6-r0 \
    bash=5.2.15-r5 \
    openrc=0.47.1-r0 \
    openssh=9.3_p1-r3 \
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
    mkdir -pv /var/log/openvswitch/


COPY init /root/init
# Add supervisord configuration file
COPY supervisord.conf /etc/supervisord.conf
COPY orchestrator.py /root/orchestrator.py
COPY ovs-docker /usr/bin/ovs-docker

ENV DEBUG no

ENTRYPOINT [ "/root/init" ]
