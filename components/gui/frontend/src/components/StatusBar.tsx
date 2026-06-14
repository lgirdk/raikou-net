import styles from './StatusBar.module.css'

interface StatusBarProps {
  connected: boolean
  containerCount: number
  bridgeCount: number
  vethCount: number
}

export default function StatusBar({
  connected,
  containerCount,
  bridgeCount,
  vethCount,
}: StatusBarProps) {
  return (
    <footer className={`${styles.bar} ${connected ? styles.ok : styles.err}`}>
      <span className={styles.dot} />
      <span>
        {connected
          ? `Connected · ${containerCount} containers · ${bridgeCount} bridges · ${vethCount} veth pairs`
          : 'Connecting…'}
      </span>
      <div className={styles.spacer} />
      <span className={styles.host}>localhost:8090</span>
    </footer>
  )
}
