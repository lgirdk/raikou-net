# bind library build stage.
FROM python:3.12.4-slim-bookworm AS build-stage

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
# The following lines compile a shim to bind a process to an IP address
# using LD_PRELOAD. To run the shim use the following syntax:
# BIND_ADDR="X.X.X.X" LD_PRELOAD=/usr/lib/bind.so [command to run]
RUN wget -q http://daniel-lange.com/software/bind.c -O bind.c \
    && sed -i '/#include <errno.h>/a #include <arpa\/inet.h>' bind.c \
    && gcc -nostartfiles -fpic -shared bind.c -o bind.so -ldl -D_GNU_SOURCE \
    && strip bind.so


# Debian SSH server start from here.
FROM python:3.12.4-slim-bookworm

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="1.9.2p1"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "root:bigfoot1" | chpasswd

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /var/run/sshd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*GatewayPorts.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config
EXPOSE 22/tcp

# Copy bind.so shared library from previous stage.
COPY --from=build-stage /root/bind.so /usr/lib/
COPY isolate_docker_iface /usr/bin/

ENV TIMEOUT 60

CMD ["/usr/sbin/sshd", "-D"]
