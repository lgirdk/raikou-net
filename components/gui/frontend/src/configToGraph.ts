import type { Edge, Node } from '@xyflow/react'
import type {
  BridgeNodeData,
  ContainerNodeData,
  OrchestratorConfig,
  VethNodeData,
} from './types'

// Layout constants — bridges in the left column, containers/veths on the right.
const BRIDGE_X = 80
const RIGHT_X = 440
const ROW_HEIGHT = 100

export function configToGraph(config: OrchestratorConfig): {
  nodes: Node[]
  edges: Edge[]
} {
  const nodes: Node[] = []
  const edges: Edge[] = []

  // ── Bridges ──────────────────────────────────────────────────────────
  let bridgeY = 80
  for (const [name] of Object.entries(config.bridge)) {
    nodes.push({
      id: `bridge:${name}`,
      type: 'bridge',
      position: { x: BRIDGE_X, y: bridgeY },
      data: { label: name } satisfies BridgeNodeData,
    })
    bridgeY += ROW_HEIGHT
  }

  // ── Containers ───────────────────────────────────────────────────────
  let rightY = 80
  for (const [name, ifaces] of Object.entries(config.container)) {
    const nodeData: ContainerNodeData = {
      label: name,
      ifaces: ifaces.map((i) => ({
        bridge: i.bridge,
        iface: i.iface,
        ipaddress: i.ipaddress,
        ip6address: i.ip6address,
        gateway: i.gateway,
      })),
    }
    nodes.push({
      id: `container:${name}`,
      type: 'container',
      position: { x: RIGHT_X, y: rightY },
      data: nodeData,
    })
    rightY += ROW_HEIGHT

    // One edge per bridge attachment.
    for (const iface of ifaces) {
      edges.push({
        id: `edge:${iface.bridge}-${name}-${iface.iface}`,
        source: `bridge:${iface.bridge}`,
        target: `container:${name}`,
        label: iface.iface,
        style: { stroke: 'var(--edge-ct)', strokeWidth: 2 },
        labelStyle: { fill: 'var(--edge-lbl)', fontSize: 10 },
        labelBgStyle: { fill: 'var(--bg)', fillOpacity: 0.85 },
      })
    }
  }

  // ── Veth pairs ───────────────────────────────────────────────────────
  for (const veth of config.veth_pairs) {
    const nodeData: VethNodeData = {
      label: veth.id,
      on: veth.on,
      map: veth.map,
    }
    nodes.push({
      id: `veth:${veth.id}`,
      type: 'veth',
      position: { x: RIGHT_X, y: rightY },
      data: nodeData,
    })
    rightY += ROW_HEIGHT

    edges.push({
      id: `edge:veth-${veth.id}`,
      source: `bridge:${veth.on}`,
      target: `veth:${veth.id}`,
      label: veth.map ?? veth.id,
      style: {
        stroke: 'var(--edge-vt)',
        strokeWidth: 2,
        strokeDasharray: '6,3',
      },
      labelStyle: { fill: 'var(--vt-name)', fontSize: 10 },
      labelBgStyle: { fill: 'var(--bg)', fillOpacity: 0.85 },
    })
  }

  return { nodes, edges }
}
