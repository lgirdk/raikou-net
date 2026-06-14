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
import type { SelectedNode } from './types'
import styles from './App.module.css'

type ModalKind = 'bridge' | 'container' | 'veth' | null

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [selected, setSelected] = useState<SelectedNode | null>(null)
  const [modal, setModal] = useState<ModalKind>(null)
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)

  const { nodes, edges, config, loading, error, refresh } = useConfig()
  const { ops, stageOp, unstageOp, clearOps, applyOps, applying, applyResult } = useStaged()

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
    { label: '+ Add bridge',    onClick: () => setModal('bridge')    },
    { label: '+ Add iface',     onClick: () => setModal('container') },
    { label: '+ Add veth pair', onClick: () => setModal('veth')      },
  ]

  const containerCount = config ? Object.keys(config.container).length : 0
  const bridgeCount    = config ? Object.keys(config.bridge).length : 0
  const vethCount      = config ? (config.veth_pairs?.length ?? 0) : 0

  async function handleApply() {
    await applyOps()
    void refresh()
  }

  return (
    <div className={styles.app}>
      <Toolbar
        theme={theme}
        onToggleTheme={toggleTheme}
        stagedCount={ops.length}
        onApply={handleApply}
        applying={applying}
      />

      <div className={styles.main}>
        <StagedPanel
          ops={ops}
          onRemove={unstageOp}
          onClear={clearOps}
          applyResult={applyResult}
        />

        {loading && <div className={styles.loading}>Loading topology…</div>}
        {error   && <div className={styles.error}>Error: {error}</div>}
        {!loading && !error && (
          <div style={{ flex: 1, position: 'relative' }} onContextMenu={handlePaneContextMenu}>
            <Canvas
              initialNodes={nodes}
              initialEdges={edges}
              onSelectNode={setSelected}
            />
          </div>
        )}

        <RightPanel
          selected={selected}
          onStageRemove={(node) => {
            if (node.type === 'container') {
              stageOp({ kind: 'remove_container', containerName: node.data.label })
            } else if (node.type === 'veth') {
              stageOp({ kind: 'remove_veth_pair', id: node.data.label })
            }
            // bridge removal not wired in Phase E
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
        <AddBridgeModal onClose={() => setModal(null)} onStage={stageOp} />
      )}
      {modal === 'container' && (
        <AddContainerIfaceModal onClose={() => setModal(null)} onStage={stageOp} config={config} />
      )}
      {modal === 'veth' && (
        <AddVethPairModal onClose={() => setModal(null)} onStage={stageOp} config={config} />
      )}
    </div>
  )
}
