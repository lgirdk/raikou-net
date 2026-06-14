import { useEffect, useRef, useState } from 'react'
import type { OrchestratorConfig, StagedOp } from '../types'
import styles from './Modals.module.css'

// ── Base modal wrapper ───────────────────────────────────────────────────────

interface ModalProps {
  title: string
  onClose: () => void
  onSubmit: () => void
  submitLabel?: string
  children: React.ReactNode
}

function Modal({ title, onClose, onSubmit, submitLabel = 'Stage', children }: ModalProps) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div ref={ref} className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.dialogHeader}>
          <span className={styles.dialogTitle}>{title}</span>
          <button className={styles.closeBtn} onClick={onClose}>×</button>
        </div>
        <div className={styles.body}>{children}</div>
        <div className={styles.footer}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.submitBtn} onClick={onSubmit}>{submitLabel}</button>
        </div>
      </div>
    </div>
  )
}

// ── Field helper ─────────────────────────────────────────────────────────────

function Field({
  label, value, onChange, placeholder, help,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  help?: string
}) {
  return (
    <div className={styles.field}>
      <label className={styles.fieldLabel}>{label}</label>
      <input
        className={styles.input}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {help && <span className={styles.fieldHelp}>{help}</span>}
    </div>
  )
}

// ── AddBridgeModal ───────────────────────────────────────────────────────────

interface AddBridgeModalProps {
  onClose: () => void
  onStage: (op: StagedOp) => void
}

export function AddBridgeModal({ onClose, onStage }: AddBridgeModalProps) {
  const [name, setName] = useState('')
  const [iprange, setIprange] = useState('')
  const [ip6range, setIp6range] = useState('')

  function submit() {
    if (!name.trim()) return
    onStage({
      kind: 'add_bridge',
      name: name.trim(),
      info: {
        ...(iprange.trim() && { iprange: iprange.trim() }),
        ...(ip6range.trim() && { ip6range: ip6range.trim() }),
      },
    })
    onClose()
  }

  return (
    <Modal title="Add Bridge" onClose={onClose} onSubmit={submit}>
      <Field label="Bridge name *" value={name} onChange={setName} placeholder="e.g. lan-bridge" />
      <Field
        label="IPv4 range"
        value={iprange}
        onChange={setIprange}
        placeholder="e.g. 192.168.1.0/24"
        help="Optional — used for DHCP allocation"
      />
      <Field label="IPv6 range" value={ip6range} onChange={setIp6range} placeholder="e.g. fd00::/64" />
    </Modal>
  )
}

// ── AddContainerIfaceModal ───────────────────────────────────────────────────

interface AddContainerIfaceModalProps {
  onClose: () => void
  onStage: (op: StagedOp) => void
  config: OrchestratorConfig | null
}

export function AddContainerIfaceModal({
  onClose, onStage, config,
}: AddContainerIfaceModalProps) {
  const bridges = config ? Object.keys(config.bridge) : []
  const containers = config ? Object.keys(config.container) : []

  const [containerName, setContainerName] = useState('')
  const [bridge, setBridge] = useState(bridges[0] ?? '')
  const [iface, setIface] = useState('')
  const [vlan, setVlan] = useState('')
  const [ipaddress, setIpaddress] = useState('')
  const [gateway, setGateway] = useState('')

  function submit() {
    if (!containerName.trim() || !bridge || !iface.trim()) return
    onStage({
      kind: 'add_container_iface',
      containerName: containerName.trim(),
      iface: {
        bridge,
        iface: iface.trim(),
        ...(vlan.trim() && { vlan: vlan.trim() }),
        ...(ipaddress.trim() && { ipaddress: ipaddress.trim() }),
        ...(gateway.trim() && { gateway: gateway.trim() }),
      },
    })
    onClose()
  }

  return (
    <Modal title="Add Container Interface" onClose={onClose} onSubmit={submit}>
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Container *</label>
        <input
          className={styles.input}
          list="container-list"
          value={containerName}
          onChange={(e) => setContainerName(e.target.value)}
          placeholder="container name"
        />
        <datalist id="container-list">
          {containers.map((c) => <option key={c} value={c} />)}
        </datalist>
      </div>
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Bridge *</label>
        <select
          className={styles.input}
          value={bridge}
          onChange={(e) => setBridge(e.target.value)}
        >
          {bridges.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>
      <Field label="Interface name *" value={iface} onChange={setIface} placeholder="e.g. eth1" />
      <Field label="VLAN" value={vlan} onChange={setVlan} placeholder="e.g. 100" />
      <Field label="IP address" value={ipaddress} onChange={setIpaddress} placeholder="e.g. 10.0.0.2/24" />
      <Field label="Gateway" value={gateway} onChange={setGateway} placeholder="e.g. 10.0.0.1" />
    </Modal>
  )
}

// ── AddVethPairModal ─────────────────────────────────────────────────────────

interface AddVethPairModalProps {
  onClose: () => void
  onStage: (op: StagedOp) => void
  config: OrchestratorConfig | null
}

export function AddVethPairModal({ onClose, onStage, config }: AddVethPairModalProps) {
  const bridges = config ? Object.keys(config.bridge) : []
  const [id, setId] = useState('')
  const [on, setOn] = useState(bridges[0] ?? '')
  const [map, setMap] = useState('')

  function submit() {
    if (!id.trim() || !on) return
    onStage({
      kind: 'add_veth_pair',
      id: id.trim(),
      on,
      ...(map.trim() && { map: map.trim() }),
    })
    onClose()
  }

  return (
    <Modal title="Add Veth Pair" onClose={onClose} onSubmit={submit}>
      <Field
        label="Pair ID * (≤8 chars)"
        value={id}
        onChange={setId}
        placeholder="e.g. cpe-lan"
      />
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Bridge *</label>
        <select
          className={styles.input}
          value={on}
          onChange={(e) => setOn(e.target.value)}
        >
          {bridges.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>
      <Field label="VLAN map" value={map} onChange={setMap} placeholder="e.g. 100:200" />
    </Modal>
  )
}
