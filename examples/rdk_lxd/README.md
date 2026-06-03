# rdk_lxd — prplos bench with an RDK-generic LXD CPE

Same topology as [`../prplos`](../prplos), but the CPE is a **RDK-generic
image** running as an **LXD container** instead of the PrplOS Docker `cpe` service.

```
router(cpe) ── cpe-rtr ── eth0  [ RDK CPE (LXD) ]  eth1 ── lan-cpe ── lan
                                                  (wlan0-3 optional)
router(eth1) ── rtr-wan ── wan, dhcp, acs
router(aux0) ── rtr-uplink            (stub for an external uplink)
```

The orchestrator runs with `USE_LINUX_BRIDGE=true`, so `cpe-rtr`/`lan-cpe` are plain
Linux bridges. The CPE attaches with `nictype=bridged parent=cpe-rtr|lan-cpe`.

## One-time: publish the RDK rootfs to GHCR

The ~50 MB rootfs is **not** committed. Publish it once as an OCI artifact (same
registry as the service images):

```bash
oras push ghcr.io/ketantewari/raikou/rdk-rootfs:qemux86broadband \
    rdk-generic-broadband-image-qemux86broadband.lxc.tar.bz2
```

Make the GHCR package **public**, or the VM will need a token for `oras pull`
(`oras login ghcr.io -u <user> -p <token>` before `vagrant up`). Override the
reference with the `RDK_ROOTFS_REF` env var or `.env`.

## Run

```bash
vagrant up                      # VirtualBox or libvirt
ENABLE_WIFI=1 vagrant up        # also attach 4 virtual wlan radios to the CPE
```

Published services are forwarded to `localhost:<port>` (e.g. acs UI on 3000, ssh on
4000/4001/…). The CPE is reachable inside the VM:

```bash
vagrant ssh
lxc list
lxc exec rdk-cpe -- ip addr
```

## Lifecycle

A systemd unit (`raikou-rdk-lxd.service`) runs `bench-up.sh` on start and
`bench-down.sh` on stop. Manually:

```bash
vagrant ssh -c 'cd /vagrant && sudo ./bench-down.sh'   # tear down CPE + stack
vagrant ssh -c 'cd /vagrant && sudo ./bench-up.sh'     # bring back up
```

## Configuration

| Var | Default | Meaning |
| --- | --- | --- |
| `VERSION` | `v3` | tag for the ghcr service images |
| `RDK_ROOTFS_REF` | `ghcr.io/ketantewari/raikou/rdk-rootfs:qemux86broadband` | OCI ref (tag) for the rootfs to pull (e.g. swap to the bpi tag) |
| `RDK_IMAGE` | newest `images/*.tar.bz2` | explicit rootfs path; overrides the auto-pick when multiple tags were pulled |
| `ENABLE_WIFI` | `0` | attach wlan0-3 to the CPE when `1` |
| `CUST_ID` | `8` | passed to `set_customerID_pp` inside the CPE |
