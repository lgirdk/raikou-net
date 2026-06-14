import { useCallback, useState } from 'react'
import type { ApplyResult, StagedOp } from './types'

export function useStaged() {
  const [ops, setOps] = useState<StagedOp[]>([])
  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null)
  const [applying, setApplying] = useState(false)

  const stageOp = useCallback((op: StagedOp) => {
    setOps((prev) => [...prev, op])
  }, [])

  const unstageOp = useCallback((index: number) => {
    setOps((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const clearOps = useCallback(() => setOps([]), [])

  const applyOps = useCallback(async () => {
    setApplying(true)
    setApplyResult(null)
    let succeeded = 0

    for (const op of ops) {
      try {
        if (op.kind === 'add_bridge') {
          const res = await fetch('/api/add_bridge', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ bridge_name: op.name, bridge_info: op.info }),
          })
          if (!res.ok) throw new Error(await res.text())
        } else if (op.kind === 'add_container_iface') {
          const res = await fetch('/api/add_container_iface', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ container_id: op.containerName, container_info: op.iface }),
          })
          if (!res.ok) throw new Error(await res.text())
        } else if (op.kind === 'add_veth_pair') {
          const res = await fetch('/api/add_veth_pair', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({
              veth_pair_id: op.id,
              veth_pair_info: { on: op.on, map: op.map },
            }),
          })
          if (!res.ok) throw new Error(await res.text())
        } else if (op.kind === 'remove_container_iface') {
          const res = await fetch(`/api/container/${op.containerName}/iface`, {
            method: 'DELETE',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ bridge: op.bridge, iface: op.iface }),
          })
          if (!res.ok) throw new Error(await res.text())
        } else if (op.kind === 'remove_container') {
          const res = await fetch(`/api/container/${op.containerName}`, {
            method: 'DELETE',
          })
          if (!res.ok) throw new Error(await res.text())
        } else if (op.kind === 'remove_veth_pair') {
          const res = await fetch(`/api/veth/${op.id}`, { method: 'DELETE' })
          if (!res.ok) throw new Error(await res.text())
        }
        succeeded++
      } catch (err) {
        setApplyResult({
          succeeded,
          failed: ops.length - succeeded,
          failedOp: op,
          error: err instanceof Error ? err.message : String(err),
        })
        setApplying(false)
        return
      }
    }

    setOps([])
    setApplyResult({ succeeded, failed: 0 })
    setApplying(false)
  }, [ops])

  return { ops, stageOp, unstageOp, clearOps, applyOps, applying, applyResult }
}
