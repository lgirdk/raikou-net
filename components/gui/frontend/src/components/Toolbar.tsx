import styles from './Toolbar.module.css'

interface ToolbarProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  stagedCount?: number
  onApply?: () => void | Promise<void>
  applying?: boolean
}

export default function Toolbar({
  theme,
  onToggleTheme,
  stagedCount = 0,
  onApply,
  applying = false,
}: ToolbarProps) {
  return (
    <header className={styles.toolbar}>
      <img className={styles.logo} src="/raikou-banner.jpg" alt="Raikou-Net" />
      <div className={styles.spacer} />
      {stagedCount > 0 && !applying && (
        <span className={styles.pendingLbl}>{stagedCount} staged</span>
      )}
      <button
        className={`${styles.btn} ${styles.applyBtn}`}
        onClick={onApply}
        disabled={stagedCount === 0 || applying}
      >
        {applying ? 'Applying…' : 'Apply'}
        {stagedCount > 0 && !applying && (
          <span className={styles.badge}>{stagedCount}</span>
        )}
      </button>
      <div className={styles.divider} />
      <button className={styles.themeBtn} onClick={onToggleTheme} title="Toggle light/dark">
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>
    </header>
  )
}
