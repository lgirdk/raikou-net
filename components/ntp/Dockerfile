FROM ssh:v2.0.0

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="container_utils_1.1.1"

ENV LEGACY="no"
ENV NTP_UPSTREAM=
ENV DEBIAN_FRONTEND=noninteractive

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    xinetd \
    ntpsec && \
    rm -rf /var/lib/apt/lists/*

COPY ./init /root/init
# Defaults ship to /etc/ntpsec.dist/ — init copies into /etc/ntpsec/ only if
# no override is mounted, so compose can bind-mount /etc/ntpsec/ntp.conf.
COPY ./ntp.conf /etc/ntpsec.dist/ntp.conf

CMD ["/root/init"]
