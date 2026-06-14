import { useCallback } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { Node } from '@xyflow/react'
import BridgeNode from '../nodes/BridgeNode'
import ContainerNode from '../nodes/ContainerNode'
import VethNode from '../nodes/VethNode'
import type { SelectedNode } from '../types'

// nodeTypes tells React Flow which component to use for each node type string.
// These must be defined OUTSIDE the component to avoid re-registration on
// every render (a common React Flow gotcha).
const nodeTypes = {
  bridge: BridgeNode,
  container: ContainerNode,
  veth: VethNode,
}

interface CanvasProps {
  initialNodes: Node[]
  initialEdges: ReturnType<typeof useEdgesState>[0]
  onSelectNode: (node: SelectedNode | null) => void
}

export default function Canvas({ initialNodes, initialEdges, onSelectNode }: CanvasProps) {
  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  const selectFromNode = useCallback(
    (node: Node) => {
      const [typeStr, ...rest] = node.id.split(':')
      const id = rest.join(':')
      if (typeStr === 'bridge') {
        onSelectNode({ type: 'bridge', id, data: node.data as never })
      } else if (typeStr === 'container') {
        onSelectNode({ type: 'container', id, data: node.data as never })
      } else if (typeStr === 'veth') {
        onSelectNode({ type: 'veth', id, data: node.data as never })
      }
    },
    [onSelectNode],
  )

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => selectFromNode(node),
    [selectFromNode],
  )

  const handleNodeDragStart = useCallback(
    (_: MouseEvent | TouchEvent, node: Node) => selectFromNode(node),
    [selectFromNode],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      onNodeDragStart={handleNodeDragStart}
      onPaneClick={() => onSelectNode(null)}
      fitView
    >
      <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="var(--dot)" />
      <Controls />
      <MiniMap
        nodeColor={(n) => {
          if (n.type === 'bridge') return 'var(--br-bd)'
          if (n.type === 'veth') return 'var(--vt-bd)'
          return 'var(--ct-bd)'
        }}
      />
    </ReactFlow>
  )
}
