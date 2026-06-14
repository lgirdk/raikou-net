import { useEffect } from 'react'
import styles from './ContextMenu.module.css'

interface ContextMenuItem {
  label: string
  onClick: () => void
}

interface ContextMenuProps {
  x: number
  y: number
  items: ContextMenuItem[]
  onClose: () => void
}

export default function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  useEffect(() => {
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', keyHandler)
    return () => window.removeEventListener('keydown', keyHandler)
  }, [onClose])

  return (
    <>
      {/* Transparent full-screen backdrop — any click outside closes the menu */}
      <div className={styles.backdrop} onClick={onClose} />
      <ul className={styles.menu} style={{ left: x, top: y }}>
        {items.map((item) => (
          <li
            key={item.label}
            className={styles.item}
            onClick={() => { item.onClick(); onClose() }}
          >
            {item.label}
          </li>
        ))}
      </ul>
    </>
  )
}
