import type { Edge, Node } from '@xyflow/react'
import type {
  BridgeNodeData,
  ContainerNodeData,
  OrchestratorConfig,
  VethNodeData,
} from './types'

// Horizontal step per BFS depth level, vertical gap within a column.
const X_PER_COL = 290
const Y_PER_ROW = 110

// ── Graph-based layout ────────────────────────────────────────────────────
// Every bridge, container, and veth is a vertex.  Edges come from
// container-iface → bridge connections.  BFS from the leftmost leaf bridge
// assigns a column depth to each vertex; nodes in the same column spread
// vertically.  Disconnected sub-graphs are stacked below each other.

function layoutPositions(
  config: OrchestratorConfig,
): Map<string, { x: number; y: number }> {
  // Build undirected adjacency.
  const adj = new Map<string, Set<string>>()
  const touch = (id: string) => {
    if (!adj.has(id)) adj.set(id, new Set())
  }

  for (const b of Object.keys(config.bridge))    touch(`bridge:${b}`)
  for (const c of Object.keys(config.container)) touch(`container:${c}`)
  for (const v of config.veth_pairs ?? [])        touch(`veth:${v.id}`)

  for (const [c, ifaces] of Object.entries(config.container)) {
    for (const iface of ifaces) {
      adj.get(`container:${c}`)!.add(`bridge:${iface.bridge}`)
      adj.get(`bridge:${iface.bridge}`)!.add(`container:${c}`)
    }
  }
  for (const v of config.veth_pairs ?? []) {
    adj.get(`veth:${v.id}`)!.add(`bridge:${v.on}`)
    adj.get(`bridge:${v.on}`)!.add(`veth:${v.id}`)
  }

  // Split into connected components.
  const seen = new Set<string>()
  const components: string[][] = []
  for (const seed of adj.keys()) {
    if (seen.has(seed)) continue
    const comp: string[] = []
    const q = [seed]
    seen.add(seed)
    while (q.length) {
      const cur = q.shift()!
      comp.push(cur)
      for (const nb of adj.get(cur) ?? []) {
        if (!seen.has(nb)) {
          seen.add(nb)
          q.push(nb)
        }
      }
    }
    components.push(comp)
  }

  const positions = new Map<string, { x: number; y: number }>()
  let yBase = 0

  for (const comp of components) {
    // Start BFS from a degree-1 bridge (network edge), then any leaf, then first.
    const startId =
      comp.find(
        (id) => id.startsWith('bridge:') && (adj.get(id)?.size ?? 0) === 1,
      ) ??
      comp.find((id) => (adj.get(id)?.size ?? 0) <= 1) ??
      comp[0]

    // BFS within the component to assign column depths.
    const depth = new Map<string, number>()
    const q = [startId]
    depth.set(startId, 0)
    while (q.length) {
      const cur = q.shift()!
      const d = depth.get(cur)!
      for (const nb of adj.get(cur) ?? []) {
        if (!depth.has(nb)) {
          depth.set(nb, d + 1)
          q.push(nb)
        }
      }
    }

    // Group nodes by column; bridges sort before containers within a column.
    const cols = new Map<number, string[]>()
    for (const [id, d] of depth) {
      const col = cols.get(d) ?? []
      col.push(id)
      cols.set(d, col)
    }
    for (const ids of cols.values()) {
      ids.sort((a, b) => {
        const rank = (id: string) =>
          id.startsWith('bridge:') ? 0 : id.startsWith('container:') ? 1 : 2
        return rank(a) - rank(b)
      })
    }

    // Height of this component = tallest column.
    const compHeight = Math.max(...[...cols.values()].map((ids) => ids.length))

    for (const [d, ids] of cols) {
      ids.forEach((id, i) => {
        positions.set(id, {
          x: d * X_PER_COL,
          y: yBase + (i - (ids.length - 1) / 2) * Y_PER_ROW,
        })
      })
    }

    // Stack next component below, with a gap.
    yBase += compHeight * Y_PER_ROW + 260
  }

  return positions
}

// ── Handle ID convention ──────────────────────────────────────────────────
//   container iface  →  "${containerName}:${ifaceName}"   e.g. "cpe:eth0"
//   veth pair        →  "veth:${vethId}"

export function configToGraph(config: OrchestratorConfig): {
  nodes: Node[]
  edges: Edge[]
} {
  const nodes: Node[] = []
  const edges: Edge[] = []

  // ── Compute layout positions first (needed for side computation) ─────────
  const pos = layoutPositions(config)

  // ── Helper: which side of `fromId` faces toward `toId` ───────────────────
  // Returns 'right' if toId is at a greater X (or equal), 'left' otherwise.
  const facingSide = (
    fromId: string,
    toId: string,
  ): 'left' | 'right' => {
    const fx = pos.get(fromId)?.x ?? 0
    const tx = pos.get(toId)?.x ?? 0
    return tx >= fx ? 'right' : 'left'
  }

  // ── Pre-compute per-bridge connection lists with sides ────────────────────
  const bridgeConns: Record<
    string,
    Array<{ handleId: string; side: 'left' | 'right' }>
  > = {}
  const addConn = (bridge: string, handleId: string, peerId: string) => {
    const side = facingSide(`bridge:${bridge}`, peerId)
    ;(bridgeConns[bridge] ??= []).push({ handleId, side })
  }
  for (const [name, ifaces] of Object.entries(config.container)) {
    for (const iface of ifaces)
      addConn(iface.bridge, `${name}:${iface.iface}`, `container:${name}`)
  }
  for (const veth of config.veth_pairs ?? []) {
    addConn(veth.on, `veth:${veth.id}`, `veth:${veth.id}`)
  }

  // ── Build bridge nodes ─────────────────────────────────────────────────
  for (const name of Object.keys(config.bridge)) {
    const id = `bridge:${name}`
    nodes.push({
      id,
      type: 'bridge',
      position: pos.get(id) ?? { x: 0, y: 0 },
      data: {
        label: name,
        connections: bridgeConns[name] ?? [],
      } satisfies BridgeNodeData,
    })
  }

  // ── Build container nodes + edges ──────────────────────────────────────
  for (const [name, ifaces] of Object.entries(config.container)) {
    const id = `container:${name}`
    const nodeData: ContainerNodeData = {
      label: name,
      ifaces: ifaces.map((i) => ({
        bridge: i.bridge,
        iface: i.iface,
        // Side of this handle = whichever side the bridge is on.
        side: facingSide(id, `bridge:${i.bridge}`),
        ipaddress: i.ipaddress,
        ip6address: i.ip6address,
        gateway: i.gateway,
      })),
    }
    nodes.push({
      id,
      type: 'container',
      position: pos.get(id) ?? { x: 0, y: 0 },
      data: nodeData,
    })
    for (const iface of ifaces) {
      const handleId = `${name}:${iface.iface}`
      edges.push({
        id: `edge:${iface.bridge}-${name}-${iface.iface}`,
        source: `bridge:${iface.bridge}`,
        sourceHandle: handleId,
        target: id,
        targetHandle: handleId,
        style: { stroke: 'var(--edge-ct)', strokeWidth: 2 },
      })
    }
  }

  // ── Build veth nodes + edges ───────────────────────────────────────────
  for (const veth of config.veth_pairs ?? []) {
    const id = `veth:${veth.id}`
    const handleId = `veth:${veth.id}`
    nodes.push({
      id,
      type: 'veth',
      position: pos.get(id) ?? { x: 0, y: 0 },
      data: {
        label: veth.id,
        on: veth.on,
        map: veth.map,
        // Side of the target handle = whichever side the bridge is on.
        targetSide: facingSide(id, `bridge:${veth.on}`),
      } satisfies VethNodeData,
    })
    edges.push({
      id: `edge:veth-${veth.id}`,
      source: `bridge:${veth.on}`,
      sourceHandle: handleId,
      target: id,
      targetHandle: handleId,
      style: { stroke: 'var(--edge-vt)', strokeWidth: 2, strokeDasharray: '6,3' },
    })
  }

  return { nodes, edges }
}
