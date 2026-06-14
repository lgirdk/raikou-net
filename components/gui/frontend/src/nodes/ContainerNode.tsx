import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { ContainerNodeData } from '../types'
import styles from './nodes.module.css'

export default function ContainerNode({ data: rawData, selected }: NodeProps) {
  const data = rawData as ContainerNodeData
  const ifaces = data.ifaces ?? []

  const cls = [
    styles.node,
    styles.container,
    data.pending === 'add' && styles.pendingAdd,
    data.pending === 'remove' && styles.pendingRemove,
    selected && styles.selected,
  ]
    .filter(Boolean)
    .join(' ')

  const leftIfaces  = ifaces.filter((i) => i.side === 'left')
  const rightIfaces = ifaces.filter((i) => i.side === 'right')

  const renderHandles = (group: typeof ifaces, position: Position) =>
    group.map((iface, i) => (
      <Handle
        key={`${data.label}:${iface.iface}`}
        type="target"
        position={position}
        id={`${data.label}:${iface.iface}`}
        style={{ top: `${((i + 1) / (group.length + 1)) * 100}%` }}
      />
    ))

  return (
    <div className={cls}>
      {renderHandles(leftIfaces,  Position.Left)}
      {renderHandles(rightIfaces, Position.Right)}

      <div className={styles.nodeHeader}>
        <span className={styles.nodeIcon} style={{ color: 'var(--ct-bd)' }}>◻</span>
        <span className={styles.nodeName} style={{ color: 'var(--ct-name)' }}>{data.label}</span>
        <span className={`${styles.nodePill} ${styles.pillCt}`}>container</span>
      </div>

      {ifaces.length > 0 && (
        <>
          <div className={styles.ifaceDivider} />
          <div className={styles.ifaceRows}>
            {ifaces.map((i) => (
              <div key={`${i.bridge}:${i.iface}`} className={styles.ifaceRow}>
                {i.iface}
                {i.ipaddress && <span>{i.ipaddress}</span>}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
