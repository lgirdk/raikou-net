# Deployment example with OpenWRT

- Download the OpenWRT image

```shell
wget https://dl.openwrt.ai/releases/targets/x86/64/openwrt-02.01.2024-x86-64-generic-rootfs.tar.gz
```

- Once the image is downloaded, import it into docker

```shell
docker import openwrt-02.01.2024-x86-64-generic-rootfs.tar.gz openwrt
```

- Run the following command to start the OVS Orchestrator container:

   ```shell
   docker-compose up -d
   ```

- Verify that the OVS Orchestrator container is running by checking the
container logs or running `docker ps`.

