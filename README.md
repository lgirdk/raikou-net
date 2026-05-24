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

Raikou-Net is a Docker-in-Docker orchestrator that wires other containers on
the same host into a declarative network topology. It can use either
Open vSwitch (OVS, default) or plain Linux bridges as the dataplane.

The orchestrator runs `privileged`, `pid: host`, and `network_mode: host`,
mounts the host Docker socket, and pushes veth interfaces into peer
containers based on a single declarative `config.json`. It also exposes a
small FastAPI REST surface for mutating topology on the fly.


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

- Two interchangeable dataplane backends: OVS (default) or Linux bridges
  (`USE_LINUX_BRIDGE=true`)
- Declarative topology from a single `config.json`, hot-reloaded every 15s
- Attaches containers to bridges via `ovs-docker` / `lxbr-docker`
- VLAN access / trunk / native tagging on container ports
- VLAN translation via `veth_pairs` (S-VLAN ↔ C-VLAN)
- Static or auto-allocated IPv4 / IPv6 addressing, with gateway and MAC
- FastAPI REST endpoints to add/remove bridges, container ifaces, and
  veth pairs at runtime without rewriting `config.json`

## Prerequisites

Before deploying Raikou-Net, ensure that you have the following prerequisites:

- Docker installed on the host machine.
- OVS installed on the host machine (only if running with the default OVS
  backend; not required when `USE_LINUX_BRIDGE=true`).
- The `openvswitch` kernel module loadable from the host (OVS backend only).
- Basic understanding of Docker and container networking concepts.
- A properly configured `config.json` file for the topology.

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

To deploy Raikou-Net, follow these steps:

1. Clone the Raikou-Net repository.

2. Prepare the `config.json` file with the necessary topology configuration.
Ensure it is placed in the same directory as the Raikou-Net files.
For syntax details, please refer to the following page:
[Raikou-Net Configuration Syntax](./docs/CONFIG.README.md)

3. Create a `docker-compose.yml` file with the desired container dependencies and configuration.

    ```yaml
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
            environment:
                USE_LINUX_BRIDGE: "false"   # "true" -> brctl/bridge instead of OVS
                DEBUG: "no"
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

   This command builds the Raikou-Net image based on the provided Dockerfile.

5. Run the following command to start the Raikou-Net container:

   ```shell
   docker-compose up -d
   ```

   This command starts the container in detached mode,
   allowing it to run in the background.

6. Verify that the Raikou-Net container is running by checking the
container logs or running `docker ps`.

> The reconcile loop re-reads `/root/config.json` every 15 seconds, so most
> topology edits take effect without restarting the container. `docker
> compose restart raikou` is only needed if reconcile gives up after
> repeated failures.

### Environment knobs

The orchestrator container reads these env vars (defaults from the
[Dockerfile](Dockerfile)):

| Variable             | Default   | Purpose                                                                  |
| -------------------- | --------- | ------------------------------------------------------------------------ |
| `USE_LINUX_BRIDGE`   | `false`   | Use `brctl`/`bridge` instead of OVS. Skips supervisord's `ovsvswitch`.   |
| `DEBUG`              | `no`      | `yes` raises the logger level to DEBUG.                                  |
| `UVICORN_HOST`       | `0.0.0.0` | Bind address for the REST API.                                           |
| `UVICORN_PORT`       | `8080`    | Listen port for the REST API.                                            |
| `DOCKER_API_VERSION` | `1.41`    | Pinned because the bundled Docker CLI may be newer than the host daemon. |

### Overriding peer-component configs via compose mounts

Every component image under [components/](components/) ships its defaults
under a sibling `.dist/` directory (for example `/etc/kea.dist/`,
`/etc/frr.dist/`, `/etc/kamailio.dist/`, `/root/aftr.dist/`). The container's
`init` script copies any missing entry into the live path on startup, so a
`docker compose` bind-mount on the live path is treated as an authoritative
override — the baked default is left alone.

In practice that means a stanza like

```yaml
dhcp:
    image: ghcr.io/.../dhcp:v1
    volumes:
        - ./config/kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf
```

fully replaces the baked `kea-dhcp4.conf`. No mount → the baked default ships
through unchanged.

The router image goes one step further: `/etc/frr/frr.conf` is regenerated
from `/etc/frr.dist/frr.conf` on every start and then env-driven interface
blocks are appended, so restarts cannot double-append. If you bind-mount
`/etc/frr/frr.conf` the regeneration and the env-driven appends are both
skipped — the mount is treated as your authoritative copy.

### Live mutation via REST API

`uvicorn` serves a FastAPI app on `UVICORN_HOST:UVICORN_PORT` with three
routers ([app/routers/](app/routers/)):

- `/bridge`    — create / delete / inspect bridges
- `/container` — attach or detach container interfaces
- `/veth`      — create / delete VLAN-translating veth pairs

Each handler takes `EVENT_LOCK` before mutating host networking, so it is
safe to call concurrently with the 15s reconcile loop.

## How the topology configuration works

Consider we would like to have board, lan and router containers
connected to each other in the following topology:

![image](./docs/network.svg)

This can be achieved with the following steps:

#### Step 1: Create the necessary OVS bridges

We would require 2 bridges ```cpe-wan``` and ```cpe-lan``` in this case

```json
{
    "bridge": {
        "cpe-lan": {},
        "cpe-wan": {}
    }
}
```

#### Step 2: Connect container to respective bridges

LAN and board both should get connected to ```cpe-lan``` bridge
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

Board and BNG get connected to ```cpe-wan``` but with a different
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

(Only needed if the live reconcile / REST API can't apply the change.)

## Trying it out with Vagrant (`examples/double_hop/`)

[examples/double_hop/Vagrantfile](examples/double_hop/Vagrantfile) spins up
an Ubuntu 22.04 VM, installs Docker + the `openvswitch` kernel module, and
runs the full double-hop stack (orchestrator + router/wan/lan/dhcp/cpe/acs/
sip/phones/mongo). Every container port published by the compose file is
forwarded `guest == host`, so the stack is reachable at `localhost:<port>`
on your workstation.

```bash
cd examples/double_hop
vagrant up                                                      # default: docker-compose.ghcr.yaml
COMPOSE_FILE=docker-compose.yaml          vagrant up            # pick at first boot
COMPOSE_FILE=docker-compose.ghcr_rdkb.yaml vagrant provision    # switch stack on a running VM
```

Things worth knowing before you change the Vagrant setup:

- The box is `generic/ubuntu2204` because it ships both VirtualBox and
  libvirt images. `bento/*` is VirtualBox-only and hangs under libvirt at
  *"Waiting for domain to get an IP address..."*.
- The provisioner `modprobe`s `openvswitch` and persists it via
  `/etc/modules-load.d/openvswitch.conf` — the orchestrator bind-mounts
  `/lib/modules` and calls `ovs-ctl force-reload-kmod`, which fails
  without this.
- A systemd unit (`raikou-double-hop.service`) owns the compose lifecycle.
  `ExecStart` runs `up -d` on every boot, `ExecStop` runs `compose down`
  on shutdown so containers exit cleanly before `docker.service` stops.
- `COMPOSE_FILE` is baked into the unit at provision time, not read at
  boot. To switch stacks on a running VM, re-run `vagrant provision` with
  the new value (the provisioner stops the old unit first so the old
  `ExecStop` tears down the right stack).
- The synced folder uses `rsync` for provider portability. Edits to
  `config.json` or `config/kea-dhcp*.conf` on the host do **not**
  auto-propagate — run `vagrant rsync` (or `vagrant rsync-auto` in a side
  terminal) and then restart the affected container.

## Contributing

Contributions to the Raikou-Net project are welcome!
If you find any issues or have suggestions for improvement,
please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

---
