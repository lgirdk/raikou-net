FROM ubuntu:24.04 as builder

WORKDIR /root

# Downloading the latest release 3.0.3
ARG BUILD_LINK="https://gitlab.com/prpl-foundation/prplos/prplos/-/package_files/136299333/download"

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget=1.21.4-1ubuntu4.1 \
    squashfs-tools=1:4.6.1-1build1 \
    fdisk=2.39.3-9ubuntu6 && \
    wget -q ${BUILD_LINK} --no-check-certificate -O image.img && \
    offset=$(sfdisk -d image.img | grep "image.img2" | sed -E 's/.*start=\s+([0-9]+).*/\1/g') && \
    unsquashfs -no-progress -quiet -offset $(( 512 * offset )) -dest "prplos" image.img

FROM scratch

COPY --from=builder /root/prplos /

CMD ["/sbin/init"]
