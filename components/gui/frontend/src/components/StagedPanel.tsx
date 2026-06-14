import type { StagedOp } from '../types'
import styles from './StagedPanel.module.css'

interface StagedPanelProps {
  ops: StagedOp[]
  onRemove: (index: number) => void
  onClear: () => void
  applyResult: { succeeded: number; failed: number; error?: string; failedOp?: StagedOp } | null
}

function opLabel(op: StagedOp): string {
  switch (op.kind) {
    case 'add_bridge':            return `Add bridge "${op.name}"`
    case 'add_container_iface':   return `Add iface to "${op.containerName}"`
    case 'add_veth_pair':         return `Add veth "${op.id}" on "${op.on}"`
    case 'remove_container_iface': return `Remove "${op.iface}" from "${op.containerName}"`
    case 'remove_container':      return `Remove container "${op.containerName}"`
    case 'remove_veth_pair':      return `Remove veth "${op.id}"`
  }
}

function kindClass(kind: StagedOp['kind']): string {
  return kind.startsWith('remove') ? styles.kindRemove : styles.kindAdd
}

export default function StagedPanel({ ops, onRemove, onClear, applyResult }: StagedPanelProps) {
  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.title}>Staged Changes</span>
        {ops.length > 0 && (
          <button className={styles.clearBtn} onClick={onClear}>
            Clear
          </button>
        )}
      </div>

      {ops.length === 0 && (
        <p className={styles.empty}>No changes staged. Right-click the canvas to add.</p>
      )}

      <ul className={styles.list}>
        {ops.map((op, i) => (
          <li key={i} className={styles.item}>
            <span className={`${styles.kindBadge} ${kindClass(op.kind)}`}>
              {op.kind.startsWith('remove') ? '−' : '+'}
            </span>
            <span className={styles.label}>{opLabel(op)}</span>
            <button className={styles.removeBtn} onClick={() => onRemove(i)} title="Remove">
              ×
            </button>
          </li>
        ))}
      </ul>

      {applyResult && (
        <div className={applyResult.failed > 0 ? styles.errBox : styles.okBox}>
          {applyResult.failed > 0 ? (
            <>
              <strong>Failed</strong> at step {applyResult.succeeded + 1}
              {applyResult.error && (
                <div className={styles.errDetail}>{applyResult.error}</div>
              )}
            </>
          ) : (
            <strong>
              ✓ Applied {applyResult.succeeded} change
              {applyResult.succeeded !== 1 ? 's' : ''}
            </strong>
          )}
        </div>
      )}
    </aside>
  )
}
