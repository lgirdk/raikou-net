# OVS Orchestration

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

1. Clone the docker-recipes repository.

2. Prepare the `config.json` file with the necessary OVS configuration.
Ensure it is placed in the same directory as the docker-recipes/orchestrator
files.
For syntax details, please refer to the following page:
[OVS Configuration Syntax](./docs/CONFIG.README.md)

3. Update the `docker-compose.yml` file with the desired container dependencies and configuration.

    ```yaml
    version: "3.9"
    services:
      ovs:
        build:
        context: .
        dockerfile: Dockerfile
        container_name: ovs
        volumes:
            - /lib/modules:/lib/modules
            - /var/run/docker.sock:/var/run/docker.sock
            - ./config.json:/root/config.json
        privileged: true
        pid: "host"
        network_mode: "host"
        hostname: "orchestrator"
        depends_on:
            - bng
            - lan
            - board
    ```

   - Adjust the `build` section if you have customized the Dockerfile name
   or location.
   - Update the `volumes` section to map the necessary directories and files,
   including the `config.json` file.
   - Modify the `depends_on` section to include the containers that the
   orchestrator depends on.


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
        "bng": [
            {
                "bridge": "cpe-wan",
                "iface": "vl_eth0",
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
            "parent": "eno3"
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

> Note: ```parent``` will allow an OVS bridge to get connected to an actual
> physical interface on the host machine



#### Step 3. Restart the docker-compose orchestrator service
```bash
docker compose restart
```
