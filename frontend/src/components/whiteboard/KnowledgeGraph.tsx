import React, { useMemo, useCallback, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  ConnectionMode,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { getLayoutedElements } from './logic/layoutUtils'
import { processAction, initialState, WhiteboardState } from './logic/ActionEngine'
import { useProjectStore } from '@/store/project'
import { useActionStream } from '@/hooks/useActionStream'

// Custom Node Component
const KnowledgeNode = ({ data }: { data: any }) => {
  const getStyle = (type: string) => {
    switch (type) {
      case 'PB': return 'border-violet-500/50 bg-violet-900/20 shadow-[0_0_15px_rgba(139,92,246,0.3)]'
      case 'MF': return 'border-red-500/50 bg-red-900/20 shadow-[0_0_15px_rgba(239,44,44,0.3)]'
      case 'PF': return 'border-green-500/50 bg-green-900/20 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
      default: return 'border-indigo-500/50 bg-indigo-900/20 shadow-[0_0_15px_rgba(99,102,241,0.3)]'
    }
  }

  return (
    <div className={`px-4 py-2 rounded-xl border-2 backdrop-blur-md text-white min-w-[150px] text-center transition-all duration-500 ${getStyle(data.type)}`}>
      <Handle type="target" position={Position.Top} className="!bg-slate-400 !border-none !w-2 !h-2" />
      <div className="text-[10px] uppercase tracking-widest font-black opacity-50 mb-1">{data.type}</div>
      <div className="text-xs font-bold leading-tight">{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !border-none !w-2 !h-2" />
    </div>
  )
}

const nodeTypes = {
  custom: KnowledgeNode,
}

export default function KnowledgeGraph() {
  const { canvas, updateCanvasField } = useProjectStore()
  const whiteboard = canvas.whiteboard || initialState

  const [nodes, setNodes, onNodesChange] = useNodesState(whiteboard.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(whiteboard.edges)

  // Sincronização com o store
  useEffect(() => {
    updateCanvasField('whiteboard', { nodes, edges })
  }, [nodes, edges, updateCanvasField])

  const onLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges)
    setNodes([...layoutedNodes])
    setEdges([...layoutedEdges])
  }, [nodes, edges, setNodes, setEdges])

  useActionStream({
    onCanvasNode: (payload) => {
      const action = { type: 'ADD_NODE', payload: { ...payload, type: payload.type || 'PB' } }
      const nextState = processAction({ nodes, edges }, action)
      const { nodes: lNodes, edges: lEdges } = getLayoutedElements(nextState.nodes, nextState.edges)
      setNodes([...lNodes])
      setEdges([...lEdges])
    },
    onCanvasEdge: (payload) => {
      const action = { type: 'CONNECT_NODES', payload }
      const nextState = processAction({ nodes, edges }, action)
      const { nodes: lNodes, edges: lEdges } = getLayoutedElements(nextState.nodes, nextState.edges)
      setNodes([...lNodes])
      setEdges([...lEdges])
    }
  })

  // Mapear nós para tipo customizado
  const styledNodes = useMemo(() => nodes.map(n => ({ ...n, type: 'custom' })), [nodes])

  return (
    <div style={{ width: '100%', height: '100%' }} className="group relative">
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button 
          onClick={onLayout}
          className="bg-slate-800/80 hover:bg-indigo-600 text-[10px] text-white px-3 py-1.5 rounded-lg border border-white/10 backdrop-blur-md transition-all uppercase tracking-widest font-bold shadow-lg"
        >
          Recalcular Layout
        </button>
      </div>
      <ReactFlow
        nodes={styledNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        colorMode="dark"
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
      >
        <Background color="#334155" gap={16} size={1} />
        <Controls className="!bg-slate-800 !border-white/10 !fill-white" />
      </ReactFlow>
    </div>
  )
}
