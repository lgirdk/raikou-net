# Configuration Syntax

The configuration file (`config.json`) allows you to define the network
topology and container configurations for Raikou-Net. The same schema is
used whether the dataplane is OVS or Linux bridges.

The configuration follows the following syntax:

```json
{
    "bridge": {
        "bridge_name": {},
        "bridge_with_parent": {
            "parents": [
                { "iface": "parent_interface_name" }
            ]
        },
        ...
    },
    "veth_pairs": {
        "veth_prefix": {
            "on": "bridge_name",
            "map": "source_vlan:destination_vlan",
            "trunk": "no"
        },
        ...
    },
    "container": {
        "container_name": [
            {
                "bridge": "bridge_name",
                "iface": "interface_name",
                ...
            },
            ...
        ],
        ...
    }
}
```

---

## Bridge Configuration

Under the `"bridge"` section, you define the bridges you want to create.
Each bridge should be specified as a key-value pair, where the key is the
bridge name and the value is either an empty object `{}` or an object with
a `"parents"` list (and optionally `iprange` / `ip6range` / `ipaddress` /
`ip6address`).

If a bridge needs to be connected to one or more host interfaces (e.g. a
physical NIC), list them under `"parents"`. Each entry is an object with
at least an `"iface"` key, and may also carry `"vlan"`, `"trunk"`, or
`"native"` to tag traffic on that parent port:

```json
"bridge_with_parent": {
    "parents": [
        { "iface": "eno3" },
        { "iface": "eno4", "trunk": "100,200" }
    ]
}
```

---

## VLAN Translation via `veth_pairs`

The `"veth_pairs"` section lets you create a veth pair on a single bridge
where each leg is tagged with a different VLAN, effectively translating
between an S-VLAN and a C-VLAN. Each entry is keyed by a short prefix
(used to name the `v0_<prefix>` / `v1_<prefix>` interfaces, max 8 chars)
and has the following properties:

- `"on"`: The bridge to attach the veth pair to.
- `"map"`: The VLAN mapping in the format `"source_vlan:destination_vlan"`.
  Omit the destination half (e.g. `"100:"`) to leave the `v1_<prefix>` end
  dangling.
- `"trunk"` (optional): `"yes"` to attach as trunk ports instead of access
  ports. Defaults to `"no"`.

---

## Container Configuration

The `"container"` section is where you define the configurations for each
container. Each container should be specified with its name as the key, and its configurations as an array of objects. Each container configuration object
should include the following properties:

- `"bridge"`: The name of the bridge the container should be connected to.
- `"iface"`: The name of the interface within the container.
- Additional properties specific to the container, such as IP address, gateway,
VLAN, etc.

You can add configurations for multiple containers under the `"container"` section.

Please refer to the example configuration above for a better understanding of
the syntax and structure.

> Note: Make sure to mount the `config.json` file into the OVS container
> at `/root/config.json` as specified in the deployment YAML.

## Sample JSON

[Configuration Example 1](./config.example.json)
