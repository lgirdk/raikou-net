FROM ssh:v1.2.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="container_utils_1.1.1"

ENV LEGACY=yes
ENV NTP_UPSTREAM=
ENV DEBIAN_FRONTEND=noninteractive

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    xinetd \
    ntpsec && \
    rm -rf /var/lib/apt/lists/*

COPY ./init /root/init
COPY ./ntp.conf /etc/ntpsec/ntp.conf

CMD ["/root/init"]
