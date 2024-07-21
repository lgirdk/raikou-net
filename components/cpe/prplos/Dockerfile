FROM ubuntu:24.04 AS builder

WORKDIR /root

# Downloading the latest release 3.0.3
ARG BUILD_LINK="https://gitlab.com/prpl-foundation/prplos/prplos/-/package_files/136299333/download"

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    squashfs-tools \
    fdisk && \
    wget -q ${BUILD_LINK} --no-check-certificate -O image.img && \
    offset=$(sfdisk -d image.img | grep "image.img2" | sed -E 's/.*start=\s+([0-9]+).*/\1/g') && \
    unsquashfs -no-progress -quiet -offset $(( 512 * offset )) -dest "prplos" image.img

FROM scratch

COPY --from=builder /root/prplos /

CMD ["/sbin/init"]
