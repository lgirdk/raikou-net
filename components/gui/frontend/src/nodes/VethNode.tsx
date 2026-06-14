import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { VethNodeData } from '../types'
import styles from './nodes.module.css'

export default function VethNode({ data: rawData, selected }: NodeProps) {
  const data = rawData as VethNodeData

  const cls = [
    styles.node,
    styles.veth,
    data.pending === 'add' && styles.pendingAdd,
    data.pending === 'remove' && styles.pendingRemove,
    selected && styles.selected,
  ]
    .filter(Boolean)
    .join(' ')

  const targetPos = data.targetSide === 'right' ? Position.Right : Position.Left

  return (
    <div className={cls}>
      <Handle
        type="target"
        position={targetPos}
        id={`veth:${data.label}`}
      />
      <div className={styles.vethName}>{data.label}</div>
      {data.map && (
        <div className={styles.vethDetail}>
          map <span>{data.map}</span>
        </div>
      )}
    </div>
  )
}
