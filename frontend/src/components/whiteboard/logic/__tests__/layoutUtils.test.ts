import { describe, it, expect } from 'vitest'
import { getLayoutedElements } from '../layoutUtils'
import { Node, Edge } from '@xyflow/react'

describe('layoutUtils (Dagre Autolayout)', () => {
  it('deve aplicar posições aos nós baseadas na topologia', () => {
    const nodes: Node[] = [
      { id: 'n1', position: { x: 0, y: 0 }, data: { label: 'A', type: 'PB' } },
      { id: 'n2', position: { x: 0, y: 0 }, data: { label: 'B', type: 'MF' } }
    ]
    const edges: Edge[] = [
      { id: 'e1', source: 'n1', target: 'n2' }
    ]

    const { nodes: layoutedNodes } = getLayoutedElements(nodes, edges)

    // O dagre deve dar uma posição Y diferente para o n2 já que n1 -> n2
    expect(layoutedNodes[1].position.y).toBeGreaterThan(layoutedNodes[0].position.y)
    // Os nós não devem estar na mesma posição exata
    expect(layoutedNodes[0].position).not.toEqual(layoutedNodes[1].position)
  })

  it('deve lidar com grafos vazios sem quebrar', () => {
    const { nodes, edges } = getLayoutedElements([], [])
    expect(nodes).toHaveLength(0)
    expect(edges).toHaveLength(0)
  })
})
