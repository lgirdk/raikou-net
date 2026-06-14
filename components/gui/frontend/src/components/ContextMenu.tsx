import { useEffect, useRef } from 'react'
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
  const ref = useRef<HTMLUListElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('mousedown', handler)
    window.addEventListener('keydown', keyHandler)
    return () => {
      window.removeEventListener('mousedown', handler)
      window.removeEventListener('keydown', keyHandler)
    }
  }, [onClose])

  return (
    <ul ref={ref} className={styles.menu} style={{ left: x, top: y }}>
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
  )
}
