import { useState } from 'react'
import Toolbar from './components/Toolbar'
import StatusBar from './components/StatusBar'
import styles from './App.module.css'

// App is the root component. It owns theme state and will own topology
// state once we add React Flow in Phase D.
export default function App() {
  // useState returns [currentValue, setterFunction].
  // When setTheme is called, React re-renders App and everything inside it.
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  function toggleTheme() {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      // CSS class on <html> drives all the CSS custom properties in theme.css
      document.documentElement.classList.toggle('light', next === 'light')
      return next
    })
  }

  return (
    <div className={styles.app}>
      <Toolbar theme={theme} onToggleTheme={toggleTheme} />
      <div className={styles.main}>
        {/* Canvas placeholder — replaced with React Flow in Phase D */}
        <div className={styles.canvasPlaceholder}>
          <span>Canvas coming in Phase D</span>
        </div>
        {/* Right panel placeholder */}
        <aside className={styles.panel}>
          <p className={styles.panelHint}>Select a node to see details</p>
        </aside>
      </div>
      <StatusBar connected={false} containerCount={0} bridgeCount={0} vethCount={0} />
    </div>
  )
}
