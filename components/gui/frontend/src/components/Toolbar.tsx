import styles from './Toolbar.module.css'

interface ToolbarProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  onAddBridge?: () => void
  onAddContainer?: () => void
  onAddVeth?: () => void
  stagedCount?: number
  onApply?: () => void
}

// Toolbar renders the top bar. Props with ? are optional — they'll be
// wired up in Phase E when staged changes are implemented.
export default function Toolbar({
  theme,
  onToggleTheme,
  onAddBridge,
  onAddContainer,
  onAddVeth,
  stagedCount = 0,
  onApply,
}: ToolbarProps) {
  return (
    <header className={styles.toolbar}>
      <img
        className={styles.logo}
        src="/raikou-banner.jpg"
        alt="Raikou-Net"
      />
      <div className={styles.divider} />
      <button className={styles.btn} onClick={onAddBridge}>
        ⊕ Bridge
      </button>
      <button className={styles.btn} onClick={onAddContainer}>
        ⊕ Container
      </button>
      <button className={styles.btn} onClick={onAddVeth}>
        ⇄ Veth Pair
      </button>
      <div className={styles.spacer} />
      {stagedCount > 0 && (
        <span className={styles.pendingLbl}>{stagedCount} staged</span>
      )}
      <button
        className={`${styles.btn} ${styles.applyBtn}`}
        onClick={onApply}
        disabled={stagedCount === 0}
      >
        Apply
        {stagedCount > 0 && (
          <span className={styles.badge}>{stagedCount}</span>
        )}
      </button>
      <div className={styles.divider} />
      <button
        className={styles.themeBtn}
        onClick={onToggleTheme}
        title="Toggle light/dark"
      >
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>
    </header>
  )
}
