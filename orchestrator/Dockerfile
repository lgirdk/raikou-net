FROM docker:23.0.0-alpine3.17

WORKDIR /root

RUN apk add -u --no-cache openvswitch=2.17.3-r0 \
    bash=5.2.15-r0 \
    openrc=0.45.2-r7 \
    openssh=9.1_p1-r2 \
    uuidgen=2.38.1-r1 \
    iproute2=6.0.0-r1 \
    supervisor=4.2.4-r0 && \
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
COPY config.json /root/config.json
COPY ovs-docker /usr/bin/ovs-docker

ENTRYPOINT [ "/root/init" ]
