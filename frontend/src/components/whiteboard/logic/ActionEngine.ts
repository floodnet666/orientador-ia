import { z } from 'zod'
import { Node, Edge } from '@xyflow/react'

export const NodeDataSchema = z.object({
  label: z.string(),
  type: z.enum(['PB', 'MF', 'PF', 'AI']).default('AI'), // PB: Ponto de Batida, MF: Mar de Fatos, PF: Ponto de Fuga, AI: Agente Interno
})

export const ActionSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('ADD_NODE'),
    payload: z.object({
      id: z.string(),
      label: z.string(),
      type: z.enum(['PB', 'MF', 'PF', 'AI']),
    }),
  }),
  z.object({
    type: z.literal('CONNECT_NODES'),
    payload: z.object({
      source: z.string(),
      target: z.string(),
      label: z.string().optional(),
    }),
  }),
])

export type WhiteboardState = {
  nodes: Node[]
  edges: Edge[]
}

export const initialState: WhiteboardState = {
  nodes: [],
  edges: [],
}

export function processAction(state: WhiteboardState, rawAction: any): WhiteboardState {
  const result = ActionSchema.safeParse(rawAction)
  if (!result.success) return state

  const action = result.data

  switch (action.type) {
    case 'ADD_NODE': {
      const newNode: Node = {
        id: action.payload.id,
        position: { x: 0, y: 0 }, // Posição 0,0, layout será automático
        data: { label: action.payload.label, type: action.payload.type },
      }
      return {
        ...state,
        nodes: [...state.nodes, newNode],
      }
    }
    case 'CONNECT_NODES': {
      const newEdge: Edge = {
        id: `e-${action.payload.source}-${action.payload.target}`,
        source: action.payload.source,
        target: action.payload.target,
        label: action.payload.label,
      }
      return {
        ...state,
        edges: [...state.edges, newEdge],
      }
    }
    default:
      return state
  }
}
