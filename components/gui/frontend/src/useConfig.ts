import { useCallback, useEffect, useState } from 'react'
import type { Edge, Node } from '@xyflow/react'
import { configToGraph } from './configToGraph'
import type { OrchestratorConfig } from './types'

// useConfig is a custom hook. A hook is just a function that uses React's
// built-in hooks (useState, useEffect) to bundle related stateful logic.
export function useConfig() {
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [config, setConfig] = useState<OrchestratorConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // useCallback memoises the function so React doesn't re-create it
  // on every render, which would cause useEffect to loop infinitely.
  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/config')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as OrchestratorConfig
      setConfig(data)
      const { nodes: n, edges: e } = configToGraph(data)
      setNodes(n)
      setEdges(e)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  // useEffect runs once after the first render (empty dependency array []).
  useEffect(() => {
    void refresh()
  }, [refresh])

  return { nodes, setNodes, edges, setEdges, config, loading, error, refresh }
}
