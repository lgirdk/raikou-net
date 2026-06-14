import styles from './Toolbar.module.css'

interface ToolbarProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  stagedCount?: number
  onApply?: () => void | Promise<void>
  applying?: boolean
  activeTab?: string
  onTabChange?: (tab: string) => void
}

const TABS = ['Canvas']

export default function Toolbar({
  theme,
  onToggleTheme,
  stagedCount = 0,
  onApply,
  applying = false,
  activeTab = 'Canvas',
  onTabChange,
}: ToolbarProps) {
  return (
    <header className={styles.toolbar}>
      <img className={styles.logo} src="/raikou-banner.jpg" alt="Raikou-Net" />
      <span className={styles.title}>Raikou Dashboard</span>

      <div className={styles.titleSep} />

      {TABS.map((tab) => (
        <button
          key={tab}
          className={`${styles.tab} ${activeTab === tab ? styles.tabActive : ''}`}
          onClick={() => onTabChange?.(tab)}
          title={`${tab} — click to reload`}
        >
          <span className={styles.tabDot} />
          {tab}
        </button>
      ))}

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
