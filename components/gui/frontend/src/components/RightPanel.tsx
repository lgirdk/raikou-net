import type { SelectedNode } from '../types'
import styles from './RightPanel.module.css'

interface RightPanelProps {
  selected: SelectedNode | null
  // onStageRemove wired in Phase E
  onStageRemove?: (node: SelectedNode) => void
}

export default function RightPanel({ selected, onStageRemove }: RightPanelProps) {
  if (!selected) {
    return (
      <aside className={styles.panel}>
        <p className={styles.hint}>Click a node to see its details</p>
      </aside>
    )
  }

  return (
    <aside className={styles.panel}>
      <div className={styles.section}>
        <div className={styles.title}>Selected Node</div>
        <div className={styles.nameRow}>
          <span className={styles.nodeName}>{selected.id}</span>
          <span className={`${styles.tag} ${styles[`tag-${selected.type}`]}`}>
            {selected.type}
          </span>
        </div>

        {selected.type === 'bridge' && (
          <div className={styles.rows}>
            <Row label="Type" value="bridge" />
          </div>
        )}

        {selected.type === 'container' && (
          <div className={styles.rows}>
            {selected.data.ifaces.map((i) => (
              <div key={`${i.bridge}:${i.iface}`} className={styles.ifaceBlock}>
                <Row label="Bridge" value={i.bridge} blue />
                <Row label="Interface" value={i.iface} />
                {i.ipaddress && <Row label="IPv4" value={i.ipaddress} />}
                {i.ip6address && <Row label="IPv6" value={i.ip6address} small />}
                {i.gateway && <Row label="Gateway" value={i.gateway} />}
              </div>
            ))}
          </div>
        )}

        {selected.type === 'veth' && (
          <div className={styles.rows}>
            <Row label="Bridge" value={selected.data.on} blue />
            {selected.data.map && <Row label="Map" value={selected.data.map} />}
          </div>
        )}

        {onStageRemove && (
          <button className={styles.rmBtn} onClick={() => onStageRemove(selected)}>
            🗑 Stage removal
          </button>
        )}
      </div>
    </aside>
  )
}

function Row({
  label,
  value,
  blue,
  small,
}: {
  label: string
  value: string
  blue?: boolean
  small?: boolean
}) {
  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <span
        className={[styles.value, blue && styles.valueBlue, small && styles.valueSmall]
          .filter(Boolean)
          .join(' ')}
      >
        {value}
      </span>
    </div>
  )
}
