## v2.0.0 (2026-06-15)

### BREAKING CHANGE

- Changes the supervisor command
to run uvicorn instead of the python script itself.
- The config JSON syntax changes,
as VLAN translation does not exist.
- BOARDFARM-5080
- Fixes issues on mgmtd

### Feat

- **gui**: add gui service to rdk_lxd example
- **gui**: add Dockerfile and compose integration
- **gui**: inline tab, bigger logo/title, canvas glow
- **gui**: tab bar in toolbar, staged collapse btn
- **gui**: node labels, slide panels, stale fix
- **orchestrator**: add DELETE /bridge/{name} endpoint
- **gui**: staged changes, modals, Apply
- **gui**: side-aware handles + BFS layout
- **gui**: React Flow canvas with topology nodes
- **gui**: React scaffold with theme and app shell
- **gui**: add FastAPI proxy backend
- **orchestrator**: add GET /config endpoint
- **vagrant**: add private_network for remote access
- **api**: add DELETE /veth/{id} endpoint
- **api**: add container DELETE endpoints
- **orchestrator**: add removal_pass
- **orchestrator**: add iface teardown fns
- **schemas**: add RemoveContainerIface
- **utils**: add iface DB accessors
- **smoke**: lead smoke.log with the probe step/verdict transcript
- **smoke**: numbered per-step PASS/FAIL transcript with RESULT verdict
- **make**: select example via EXAMPLE=, guard smoke to prplos
- **rdk_lxd**: Vagrantfile (docker, LXD, oras)
- **rdk_lxd**: bench-up/down lifecycle wrappers
- **rdk_lxd**: merge rdk-cpe.sh up/down script
- **rdk_lxd**: docker stack + config (no CPE)
- **rdk_lxd**: scaffold example dir + assets
- **examples/double_hop**: add Vagrant dev VM and pin GHCR stack to v3
- **components**: refresh base images to trixie and unify config-override pattern
- **vcpe-rdkb**: add deployment files
- **double-hop**: compose with ghcr.io images
- **ntp**: add ntp component
- **app**: add async lock
- **veth**: add support for trunking
- **runner**: add the main fastapi entrypoint
- **veth**: add fastapi router.
- **containers**: add fastapi router.
- **bridge**: add the fastapi router
- **raikou-net**: add base fastapi requirements.
- **raikou-net**: bumped the DIND version to 27.3
- **orchestrator**: veth pair implementation
- **ovs_lib**: added VLAN setting checks.
- **ovs_lib**: breaking down the complexity
- **utils**: DB and env related functions
- **double_hop**: update docker compose and config.json with sipcenter and phones
- **dockerfile**: new dockerfile for kamailio with rtpengine
- **orchestrator**: sync MAC on service restart
- **phone**: add new dockerfile for phone
- **components**: add socks proxy support
- **raikou-net**: add support for linux bridge
- **examples**: add prplos cpe
- **cpe**: add prplos implementation
- **router**: upgrade to FRR 10.0
- **dhcp**: upgrade to KEA 2.6.0
- **sip**: add dockerfile to raikou for sipcenter
- **router**: allow support to toggle triple play
- **components**: dhcp wan router v1.1.0
- **factory**: update to v25.0.4 alpine 3.19

### Fix

- **gui**: increase Canvas tab font size to 14px
- **gui**: proper page-tab style for Canvas tab
- **orchestrator**: handle None parents in init_bridge
- **gui**: bridge schema, edit ops, ctx menu, title
- **orchestrator**: handle EBUSY on bind-mount flush
- **container**: move DELETE checks inside lock
- modprobe 802.11 hw sim modules on bootup
- **ci.yaml**: update to work with nodejs v24
- **smoke**: keep prplos unit enabled in AUTOSTART=0 so make demo still autostarts
- **smoke**: destroy the VM before each run so AUTOSTART=0 always applies
- **smoke**: gate prplos provisioner pull/autostart behind AUTOSTART
- **smoke**: run dhclient on lan before asserting its dhcp address
- **rdk_lxd**: harden Vagrant provisioner bring-up
- **rdk_lxd**: boot RDK CPE via unified LXD image
- **rdk_lxd**: resolve rootfs by *.tar.bz2 glob
- **smoke**: correct in-VM compose dir and pipe probe via stdin
- **orchestrator**: move crash supervision from main() to runner.py
- **orchestrator**: decouple API-writable config from /root/config.json
- **dockerfile**: force docker CLI version to 1.41
- **runner**: add logging for background tasks
- **orchestrator**: need to update lsmod path
- **kea**: 15s sleep for pushing on-the-fly config
- **components/ssh/Dockerfile**: upgrade python to 3 13
- **dhclient-script**: updated condition for v6 entry
- **phone_dockerfile**: use pjsua artifact instead of compiling it
- **double-hop**: use OVS by default
- **double-hop**: reorder services
- **dhcp**: keactrl paths
- **kamailio_default.cfg**: vsc parsing based on variations
- **kamailio_default.cfg**: change sip code for call forwarding
- **isolate_docker_iface**: ipv6 isolation for phone,acs,sip
- **mv3-eth-router**: docker file for mv3-eth router(frr)
- **isolate_docker_iface**: docker ipv6 network isolation for ntp,lan,dhcp and router
- **ipv6-docker-interface-isolation:-BOARDFARM-5266**: ipv6 docker interface isolation: BOARDFARM-5266
- **wan_dockerfile**: add hping3 package for wan
- **init**: addition of static routes from docker compose
- **wan/**: added aftr configuration
- **kamailio_default.cfg**: fix call forwarding logic
- **Dockerfile**: update script for aftr
- **phone_init**: change permissions of dhclient-script
- **phone_dockerfile**: add dhclient package to phone
- remove mongo from demo config
- **dhcp**: add subnet id to defaults
- **sip**: add isolate_docker_iface, add ENV and fix init.sh
- **components**: fix dockerfile directive case
- **wan,lan**: update eth1 timeout counter
- **raikou**: update ssh package version
- **lan**: update package versions
- **wan**: update package versions
- **ssh**: update package versions
- **wan**: allow mounting DNS masq host files
- **dhcp**: restart service in case no pool alloc
- **supervisor**: fix restart option for ovsd
- **supervisor**: fix process kill error

### Refactor

- **orchestrator**: veth_pairs list form
- **utils**: veth_pairs list normalization
- **utils**: rename delete_ to clear_
- **make**: rename GHCR_REGISTRY knob to REGISTRY (alias kept)
- repoint live references from double_hop to prplos
- **examples**: rename double_hop example to prplos
- **rdk_lxd**: drop SIP voice services
- **orchestrator**: replace cached-dict /tmp/db.json with sync TinyDB
- **orchestrator**: using OVS lib and utils
- **components**: remove apt/apk versioning
- **cpe**: move busybox implementation
- **sip**: refactor the labels and run commands

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
