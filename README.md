# Raikou-Net (雷光ネット)

<p align=center>
    <img src="docs/images/raikou-banner.jpg" width="500"/> <br>
    <img alt="GitHub" src="https://img.shields.io/github/license/lgirdk/raikou-net">
    <img alt="GitHub commit activity (branch)"
    src="https://img.shields.io/github/commit-activity/t/lgirdk/raikou-net">
    <img alt="GitHub last commit (branch)"
    src="https://img.shields.io/github/last-commit/lgirdk/raikou-net">
    <img alt="Python Version" src="https://img.shields.io/badge/python-3.11+-blue">
    <a href="https://github.com/psf/black"><img alt="Code style: black"
    src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
    <a href="https://github.com/astral-sh/ruff"><img alt="Code style: black"
    src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
</p> <hr>

Raikou-Net is a Docker container designed to orchestrate networking between
containers on the same host system using Open vSwitch (OVS).

It runs as a Docker-in-Docker derived image with privileged mode and leverages
the host network to create OVS bridges instead of default docker bridges.


## Benefits of Using Open vSwitch (OVS) for Docker Networking

1. **Integration with Existing Network Infrastructure:** OVS seamlessly
integrates with existing network infrastructure and can be easily connected to
physical networks, routers, and switches. This makes it ideal for hybrid
environments where Docker containers need to communicate with external systems
or legacy infrastructure.

2. **Advanced Networking Features:** OVS provides a wide range of advanced
networking features such as VLAN tagging, VXLAN overlay networks, GRE tunnels,
and more. This enables greater flexibility in designing and managing network
topologies.

3. **Performance and Scalability:** OVS is known for its high-performance
capabilities and scalability. It efficiently handles a large number of virtual
interfaces and network flows, making it suitable for complex and
demanding network environments.

4. **Network Isolation and Security:** OVS allows for finer-grained network
isolation and security controls. It supports the creation of multiple isolated
 bridges and offers features like access control lists (ACLs) and flow-based
 filtering, providing more granular control over network traffic.


5. **Interoperability and Vendor Neutrality:** OVS is an open-source project
with wide industry adoption. It is not tied to a specific vendor or platform,
offering greater interoperability and vendor neutrality. This flexibility allows
for the choice of networking solutions without vendor lock-in.

To learn more about Docker networking with OVS and how to utilize it
effectively, refer to the documentation on
[Docker Networking with Open vSwitch](https://ovs.readthedocs.io/en/latest/howto/docker.html).


## Features

- Creation of veth pairs and attachment of OVS bridges to containers
- Setting VLAN trunk/access port on container designated OVS interfaces
- Support for IPv6 address assignment
- Managing external IDs for VLAN translation

## Prerequisites

Before deploying the OVS Orchestrator, ensure that you have the following prerequisites:

- Docker installed on the host machine.
- OVS installed on the host machine
- Basic understanding of Docker and container networking concepts.
- A properly configured `config.json` file for OVS configuration.

To install openvswitch in Debian/Ubuntu:
```bash
sudo apt install openvswitch-switch openvswitch-common
```
To install openvswitch in Alpine:
```bash
sudo apk add -u openvswitch
```

To install docker engine and compose plugin, please follow the below link: <br>
[Install Docker in Ubuntu/Debian](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)


## Deployment

To deploy the OVS Orchestrator, follow these steps:

1. Clone the Raikou-Net repository.

2. Prepare the `config.json` file with the necessary OVS configuration.
Ensure it is placed in the same directory as the Raikou-Net files.
For syntax details, please refer to the following page:
[Raikou-Net OVS Configuration Syntax](./docs/README_CONFIG.md)

3. Create a `docker-compose.yml` file with the desired container dependencies and configuration.

    ```yaml
    version: "3.9"
    services:
        raikou:
            build:
                context: .
                dockerfile: Dockerfile
            container_name: raikou-net
            volumes:
                - /lib/modules:/lib/modules
                - /var/run/docker.sock:/var/run/docker.sock
                - ./config.json:/root/config.json
            privileged: true
            pid: "host"
            network_mode: "host"
            hostname: "orchestrator"
            depends_on:
                - container1
                - container2
                - container3
    ```

   - Adjust the `build` section if you have customized the Dockerfile name
   or location.
   - Update the `volumes` section to map the necessary directories and files,
   including the `config.json` file.
   - Modify the `depends_on` section to include the containers that
   raikou should handle with OVS.


4. Build the Docker image using the following command:

   ```shell
   docker-compose build
   ```

   This command builds the OVS Orchestrator image based on the provided Dockerfile.

5. Run the following command to start the OVS Orchestrator container:

   ```shell
   docker-compose up -d
   ```

   This command starts the container in detached mode,
   allowing it to run in the background.

6. Verify that the OVS Orchestrator container is running by checking the
container logs or running `docker ps`.



## How does the OVS configuration work?

Consider we would like to have board, lan and router containers
connected to each other in the following topology:

![image](./docs/network.svg)

This can be achieved with the following steps:
#### Step 1: Create the necessary OVS bridges.
We would require 2 bridges ```cpe_wan``` and ```cpe_lan``` in this case
```json
{
    "bridge": {
        "cpe-lan": {},
        "cpe-wan": {}
    }
}
```
#### Step 2: Connect container to respective bridges
LAN and board both should get connected to ```cpe_lan``` bridge
with interface name ```eth1```
```json
{
    "bridge": {
        "cpe-lan": {},
        "cpe-wan": {}
    },
    "container": {
        "lan": [
            {
                "bridge": "cpe-lan",
                "iface": "eth1"
            }
        ],
        "board": [
            {
                "bridge": "cpe-lan",
                "iface": "eth1"
            },
        ]
    }
}
```

Board and BNG get connected to ```cpe_wan``` but with a different
interface name.

We can also notice that the board needs to allow 3 VLANs on its interface
We can decide a container port to be Access VLAN port using ```vlan```
or in trunk mode using ```trunk```.

```json

{
    "bridge": {
        "cpe-lan": {},
        "cpe-wan": {}
    },
    "container": {
        "lan": [
            {
                "bridge": "cpe-lan",
                "iface": "eth1"
            }
        ],
        "board": [
            {
                "bridge": "cpe-lan",
                "iface": "eth1"
            },
            {
                "bridge": "cpe-wan",
                "iface": "eth0",
                "trunk": "131,121,117"
            }
        ],
        "router": [
            {
                "bridge": "cpe-wan",
                "iface": "eth0",
                "vlan": "121"
            },
            ...
        ]
    }
}
```

If we want to statically assing IP addresses to a container port.

```json
{
    "bridge": {
        "cpe-wan": {
            "parents": [
                {
                    "iface": "eno3"
                }
            ]
        }
    },
    "container": {
        "wan": [
            {
                "bridge": "cpe-wan",
                "iface": "eth1",
                "ipaddress": "172.25.1.101/24",
                "gateway": "172.25.1.1",
                "ip6address": "2001:dead:beef:2::101/64",
                "gateway6": "2001:dead:beef:2::1"
            }
        ]
    }
}
```

> Note: ```parents``` will allow an OVS bridge to get connected to an actual
> physical interface on the host machine


#### Step 3. Restart the docker-compose orchestrator service
```bash
docker compose restart
```

## Contributing

Contributions to the Raikou-Net project are welcome!
If you find any issues or have suggestions for improvement,
please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

---
