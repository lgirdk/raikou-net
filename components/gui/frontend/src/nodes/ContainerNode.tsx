import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { ContainerNodeData } from '../types'
import styles from './nodes.module.css'

export default function ContainerNode({ data: rawData, selected }: NodeProps) {
  const data = rawData as ContainerNodeData

  const cls = [
    styles.node,
    styles.container,
    data.pending === 'add' && styles.pendingAdd,
    data.pending === 'remove' && styles.pendingRemove,
    selected && styles.selected,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={cls}>
      <Handle type="target" position={Position.Left} />
      <div className={styles.containerName}>{data.label}</div>
      <div className={styles.ifaceRow}>
        {data.ifaces.map((i) => (
          <div key={`${i.bridge}:${i.iface}`}>
            {i.iface}
            {i.ipaddress && (
              <>
                {' · '}
                <span>{i.ipaddress}</span>
              </>
            )}
          </div>
        ))}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}
