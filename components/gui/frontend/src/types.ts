// Mirror of the orchestrator's config.json schema (app/utils.py TypedDicts).

export interface IfaceInfo {
  iface: string
  vlan?: string
  trunk?: string
  native?: string
}

export interface BridgeConfig {
  parents?: IfaceInfo[]
  iprange?: string
  ip6range?: string
  ipaddress?: string
  ip6address?: string
}

export interface ContainerIface {
  bridge: string
  iface: string
  vlan?: string
  trunk?: string
  ipaddress?: string
  ip6address?: string
  gateway?: string
  gateway6?: string
  macaddress?: string
}

export interface VethPair {
  id: string
  on: string
  map?: string
  trunk?: 'yes' | 'no'
}

export interface OrchestratorConfig {
  bridge: Record<string, BridgeConfig>
  container: Record<string, ContainerIface[]>
  veth_pairs: VethPair[]
}

// Data payloads for each React Flow node type.
// These go into the `data` prop of each node object.

export interface BridgeNodeData {
  label: string
  connections: Array<{
    handleId: string
    side: 'left' | 'right'   // which side of the bridge this handle lives on
  }>
  pending?: 'add' | 'remove'
  [key: string]: unknown
}

export interface ContainerNodeData {
  label: string
  ifaces: Array<{
    bridge: string
    iface: string
    side: 'left' | 'right'   // which side of the container this handle lives on
    ipaddress?: string
    ip6address?: string
    gateway?: string
  }>
  pending?: 'add' | 'remove'
  [key: string]: unknown
}

export interface VethNodeData {
  label: string
  on: string
  map?: string
  targetSide: 'left' | 'right'   // which side the bridge handle is on
  pending?: 'add' | 'remove'
  [key: string]: unknown
}

// ── Staged operations ────────────────────────────────────────────────────────

export type StagedOp =
  | { kind: 'add_bridge'; name: string; info: BridgeConfig }
  | { kind: 'add_container_iface'; containerName: string; iface: ContainerIface }
  | { kind: 'remove_container_iface'; containerName: string; bridge: string; iface: string }
  | { kind: 'remove_container'; containerName: string }
  | { kind: 'add_veth_pair'; id: string; on: string; map?: string }
  | { kind: 'remove_veth_pair'; id: string }

export interface ApplyResult {
  succeeded: number
  failed: number
  failedOp?: StagedOp
  error?: string
}

// Unified type used by the right panel and context menu.
export type SelectedNode =
  | { type: 'bridge'; id: string; data: BridgeNodeData }
  | { type: 'container'; id: string; data: ContainerNodeData }
  | { type: 'veth'; id: string; data: VethNodeData }
