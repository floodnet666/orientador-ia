import { describe, it, expect } from 'vitest'
import { processAction, initialState } from '../ActionEngine'

describe('ActionEngine (Deterministic Graph)', () => {
  it('deve adicionar um nó corretamente sem necessidade de coordenadas', () => {
    const action = {
      type: 'ADD_NODE',
      payload: {
        id: 'node-1',
        label: 'Tese Central',
        type: 'PB' // Ponto de Batida
      }
    }

    const nextState = processAction(initialState, action)
    expect(nextState.nodes).toHaveLength(1)
    expect(nextState.nodes[0]).toMatchObject({
      id: 'node-1',
      data: { label: 'Tese Central', type: 'PB' }
    })
  })

  it('deve conectar dois nós existentes', () => {
    const stateWithNodes = {
      nodes: [
        { id: 'n1', position: { x: 0, y: 0 }, data: { label: 'A', type: 'PB' } },
        { id: 'n2', position: { x: 0, y: 0 }, data: { label: 'B', type: 'MF' } }
      ],
      edges: []
    }

    const action = {
      type: 'CONNECT_NODES',
      payload: {
        source: 'n1',
        target: 'n2',
        label: 'sustenta'
      }
    }

    const nextState = processAction(stateWithNodes, action)
    expect(nextState.edges).toHaveLength(1)
    expect(nextState.edges[0]).toMatchObject({
      id: 'e-n1-n2',
      source: 'n1',
      target: 'n2',
      label: 'sustenta'
    })
  })

  it('deve ignorar ações com schema inválido (Zod)', () => {
    const action = { type: 'INVALID', payload: {} }
    // @ts-ignore
    const nextState = processAction(initialState, action)
    expect(nextState).toEqual(initialState)
  })
})
