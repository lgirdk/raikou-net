# OVS Configuration Syntax

The configuration file (`config.json`) allows you to define the network
topology and container configurations for your OVS orchestration.
The configuration follows the following syntax:

```json
{
    "bridge": {
        "bridge_name": {},
        "bridge_with_parent": {
            "parent": "parent_interface_name"
        },
        ...
    },
    "vlan_translations": [
        {
            "from": "source_bridge",
            "to": "destination_bridge",
            "map": "source_vlan:destination_vlan"
        },
        ...
    ],
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

Under the `"bridge"` section, you define the OVS bridges you want to create.
Each bridge should be specified as a key-value pair, where the key is the bridge
name and the value is either an empty object `{}` or an object with a `"parent"`
property.

If a bridge requires a parent interface, you can specify it by including a
`"parent"` property within the bridge object. The value of the `"parent"`
property should be the name of the parent interface.

---

## VLAN Translations

The `"vlan_translations"` section allows you to define VLAN translations
between source and destination bridges. Each VLAN translation entry should
have the following properties:

- `"from"`: The source bridge name.
- `"to"`: The destination bridge name.
- `"map"`: The VLAN mapping in the format `"source_vlan:destination_vlan"`.

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
