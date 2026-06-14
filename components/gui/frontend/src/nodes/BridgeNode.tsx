import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { BridgeNodeData } from '../types'
import styles from './nodes.module.css'

export default function BridgeNode({ data: rawData, selected }: NodeProps) {
  const data = rawData as BridgeNodeData
  const conns = data.connections ?? []

  const leftConns  = conns.filter((c) => c.side === 'left')
  const rightConns = conns.filter((c) => c.side === 'right')

  // Height is driven by whichever side has more connections.
  const nodeHeight = Math.max(46, Math.max(leftConns.length, rightConns.length) * 26 + 14)

  const cls = [
    styles.node,
    styles.bridge,
    data.pending === 'add' && styles.pendingAdd,
    data.pending === 'remove' && styles.pendingRemove,
    selected && styles.selected,
  ]
    .filter(Boolean)
    .join(' ')

  const renderHandles = (
    group: typeof conns,
    position: Position,
  ) =>
    group.map((conn, i) => (
      <Handle
        key={conn.handleId}
        type="source"
        position={position}
        id={conn.handleId}
        style={{ top: `${((i + 1) / (group.length + 1)) * 100}%` }}
      />
    ))

  return (
    <div className={cls} style={{ height: nodeHeight }}>
      {renderHandles(leftConns,  Position.Left)}
      {renderHandles(rightConns, Position.Right)}
      <span className={styles.bridgeIcon}>⬡</span>
      <span className={styles.bridgeName}>{data.label}</span>
      <span className={styles.bridgePill}>bridge</span>
    </div>
  )
}
