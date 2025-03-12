# Build Stage for bind.so
FROM node:18-buster AS bind-build-stage

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN wget -q http://daniel-lange.com/software/bind.c -O bind.c \
    && sed -i '/#include <errno.h>/a #include <arpa\/inet.h>' bind.c \
    && gcc -nostartfiles -fpic -shared bind.c -o bind.so -ldl -D_GNU_SOURCE \
    && strip bind.so


# Final Stage
FROM drumsergio/genieacs:1.2.9

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN echo "root:bigfoot1" | chpasswd

RUN mkdir /var/log/ssh

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iproute2 \
    sudo \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /var/run/sshd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*GatewayPorts.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config

ENV LEGACY="no"
ENV TIMEOUT 60

COPY --from=bind-build-stage /root/bind.so /usr/lib/

COPY isolate_docker_iface /usr/bin/

COPY ./init /root/init

EXPOSE 22/tcp

ENTRYPOINT ["/bin/bash","/root/init"]
