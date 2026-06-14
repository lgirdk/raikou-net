import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { BridgeNodeData } from '../types'
import styles from './nodes.module.css'

// NodeProps (untyped) is the v12-safe signature for custom nodes registered
// via nodeTypes. We cast `data` to our known payload type inside the component.
export default function BridgeNode({ data: rawData, selected }: NodeProps) {
  const data = rawData as BridgeNodeData

  const cls = [
    styles.node,
    styles.bridge,
    data.pending === 'add' && styles.pendingAdd,
    data.pending === 'remove' && styles.pendingRemove,
    selected && styles.selected,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={cls}>
      {/* Handles are the connection points on the node.
          Position.Left/Right tells React Flow where to draw edge endpoints. */}
      <Handle type="target" position={Position.Left} />
      <span className={styles.bridgeIcon}>⬡</span>
      <span className={styles.bridgeName}>{data.label}</span>
      <span className={styles.bridgePill}>bridge</span>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}
