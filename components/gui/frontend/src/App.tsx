import { useState } from 'react'
import Toolbar from './components/Toolbar'
import Canvas from './components/Canvas'
import RightPanel from './components/RightPanel'
import StatusBar from './components/StatusBar'
import { useConfig } from './useConfig'
import type { SelectedNode } from './types'
import styles from './App.module.css'

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [selected, setSelected] = useState<SelectedNode | null>(null)

  const { nodes, edges, config, loading, error } = useConfig()

  function toggleTheme() {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('light', next === 'light')
      return next
    })
  }

  const containerCount = config ? Object.keys(config.container).length : 0
  const bridgeCount    = config ? Object.keys(config.bridge).length : 0
  const vethCount      = config ? (config.veth_pairs?.length ?? 0) : 0

  return (
    <div className={styles.app}>
      <Toolbar theme={theme} onToggleTheme={toggleTheme} />
      <div className={styles.main}>
        {loading && <div className={styles.loading}>Loading topology…</div>}
        {error && <div className={styles.error}>Error: {error}</div>}
        {!loading && !error && (
          <Canvas
            initialNodes={nodes}
            initialEdges={edges}
            onSelectNode={setSelected}
          />
        )}
        <RightPanel selected={selected} />
      </div>
      <StatusBar
        connected={!loading && !error}
        containerCount={containerCount}
        bridgeCount={bridgeCount}
        vethCount={vethCount}
      />
    </div>
  )
}
