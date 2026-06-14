import { useCallback, useState } from 'react'
import Toolbar from './components/Toolbar'
import Canvas from './components/Canvas'
import RightPanel from './components/RightPanel'
import StagedPanel from './components/StagedPanel'
import StatusBar from './components/StatusBar'
import ContextMenu from './components/ContextMenu'
import {
  AddBridgeModal,
  AddContainerIfaceModal,
  AddVethPairModal,
} from './components/Modals'
import { useConfig } from './useConfig'
import { useStaged } from './useStaged'
import type { SelectedNode, StagedOp } from './types'
import styles from './App.module.css'

type ModalKind = 'bridge' | 'container' | 'veth' | null

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [selected, setSelected] = useState<SelectedNode | null>(null)
  const [modal, setModal] = useState<ModalKind>(null)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)
  const [userCollapsedStaged, setUserCollapsedStaged] = useState(false)

  const { nodes, edges, config, loading, error, refresh } = useConfig()
  const { ops, stageOp, unstageOp, editOp, clearOps, applyOps, applying, applyResult } = useStaged()

  function toggleTheme() {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('light', next === 'light')
      return next
    })
  }

  const handlePaneContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setCtxMenu({ x: e.clientX, y: e.clientY })
  }, [])

  const contextMenuItems = [
    { label: '+ Add bridge',    onClick: () => { setEditingIndex(null); setModal('bridge')    } },
    { label: '+ Add iface',     onClick: () => { setEditingIndex(null); setModal('container') } },
    { label: '+ Add veth pair', onClick: () => { setEditingIndex(null); setModal('veth')      } },
  ]

  // Opens the matching modal pre-filled with the op at `index`.
  function handleEditOp(index: number) {
    const op = ops[index]
    setEditingIndex(index)
    if (op.kind === 'add_bridge') setModal('bridge')
    else if (op.kind === 'add_container_iface') setModal('container')
    else if (op.kind === 'add_veth_pair') setModal('veth')
  }

  function handleModalClose() {
    setModal(null)
    setEditingIndex(null)
  }

  // Wrap stageOp to also auto-reopen the staged panel if user had collapsed it.
  function handleStageOp(op: StagedOp) {
    stageOp(op)
    setUserCollapsedStaged(false)
  }

  // When editing, replace the existing op; otherwise append a new one.
  function handleModalStage(op: StagedOp) {
    if (editingIndex !== null) {
      editOp(editingIndex, op)
    } else {
      handleStageOp(op)
    }
  }

  const containerCount = config ? Object.keys(config.container).length : 0
  const bridgeCount    = config ? Object.keys(config.bridge).length : 0
  const vethCount      = config ? (config.veth_pairs?.length ?? 0) : 0

  async function handleApply() {
    await applyOps()
    void refresh()
  }

  // Build initial values for edit modals from the staged op.
  const editingOp = editingIndex !== null ? ops[editingIndex] : undefined

  const bridgeInitial = editingOp?.kind === 'add_bridge'
    ? { name: editingOp.name, iprange: editingOp.info.iprange, ip6range: editingOp.info.ip6range }
    : undefined

  const containerInitial = editingOp?.kind === 'add_container_iface'
    ? {
        containerName: editingOp.containerName,
        bridge: editingOp.iface.bridge,
        iface: editingOp.iface.iface,
        vlan: editingOp.iface.vlan,
        ipaddress: editingOp.iface.ipaddress,
        gateway: editingOp.iface.gateway,
      }
    : undefined

  const vethInitial = editingOp?.kind === 'add_veth_pair'
    ? { id: editingOp.id, on: editingOp.on, map: editingOp.map }
    : undefined

  return (
    <div className={styles.app}>
      <Toolbar
        theme={theme}
        onToggleTheme={toggleTheme}
        stagedCount={ops.length}
        onApply={handleApply}
        applying={applying}
        onTabChange={() => void refresh()}
      />

      <div className={styles.main}>
        <StagedPanel
          ops={ops}
          collapsed={(ops.length === 0 && applyResult === null) || userCollapsedStaged}
          onRemove={unstageOp}
          onEdit={handleEditOp}
          onClear={clearOps}
          onManualCollapse={() => setUserCollapsedStaged(true)}
          applyResult={applyResult}
        />

        <div className={styles.canvasPane}>
          {loading && <div className={styles.loading}>Loading topology…</div>}
          {error   && <div className={styles.error}>Error: {error}</div>}
          {!loading && !error && (
            <div className={styles.canvasWrapper} onContextMenu={handlePaneContextMenu}>
              <Canvas
                initialNodes={nodes}
                initialEdges={edges}
                onSelectNode={setSelected}
              />
            </div>
          )}
        </div>

        <RightPanel
          selected={selected}
          onStageRemove={(node) => {
            if (node.type === 'bridge') {
              handleStageOp({ kind: 'remove_bridge', name: node.data.label })
            } else if (node.type === 'container') {
              handleStageOp({ kind: 'remove_container', containerName: node.data.label })
            } else if (node.type === 'veth') {
              handleStageOp({ kind: 'remove_veth_pair', id: node.data.label })
            }
            setSelected(null)   // clear right panel immediately after staging removal
          }}
        />
      </div>

      <StatusBar
        connected={!loading && !error}
        containerCount={containerCount}
        bridgeCount={bridgeCount}
        vethCount={vethCount}
      />

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={contextMenuItems}
          onClose={() => setCtxMenu(null)}
        />
      )}

      {modal === 'bridge' && (
        <AddBridgeModal onClose={handleModalClose} onStage={handleModalStage} initial={bridgeInitial} />
      )}
      {modal === 'container' && (
        <AddContainerIfaceModal onClose={handleModalClose} onStage={handleModalStage} config={config} initial={containerInitial} />
      )}
      {modal === 'veth' && (
        <AddVethPairModal onClose={handleModalClose} onStage={handleModalStage} config={config} initial={vethInitial} />
      )}
    </div>
  )
}
