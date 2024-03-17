## v1.0.0 (2024-01-29)

### Feat

- **examples/docker-compose.yaml**: update examples with acs
- **components/acs**: add acs example
- **Dockerfile**: update openvswitch and openssh versions
- **components**: prototype busybox cpe image
- **components**: add a router image
- **components**: add dhcp server image
- **components**: add the lan and wan host images
- **components**: add base ssh image
- **orchestrator**: add usb interface support
- **orchestrator**: add VLAN translation
- **orchestrator**: add ipv6 support
- **orchestrator**: add python script for networks
- **orchestrator**: docker-in-docker ovs alpine

### Fix

- **lan/Dockerfile**: update curl and tshark versions
- **dhcp/Dockerfile**: update curl and tshark versions
- **components/cpe/Dockerfile**: modify apt-get command to allow release info changes
- **ssh/Dockerfile**: update openssh-server version
- **router**: fix staticd issues
- **router**: fix executable path
- **router**: fix init execution permissions
- **router**: update pull version of ssh
- **orchestrator**: fix logging variable names
- **router**: update ethernet router config

### Refactor

- **raikou**: refactor the project structure
