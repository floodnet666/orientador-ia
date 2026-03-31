import { create } from 'zustand'
import { Alma } from '@/lib/api'
import { Node, Edge } from '@xyflow/react'

export interface CanvasState {
    tema: { content: string; is_locked: boolean }
    problema: { content: string; is_locked: boolean }
    justificativa: { content: string; is_locked: boolean }
    objetivos: { geral: string; especificos: string[] }
    metodologia: { tipo: string; instrumentos: string[] }
    whiteboard?: {
        nodes: Node[]
        edges: Edge[]
    }
}

export interface ChatMessage {
    id?: string
    role: 'user' | 'alma' | 'system'
    alma_name?: string | null
    content: string
    created_at?: string
}

// For compatibility we use the same structure as backend's AlmaOut
export type { Alma }

const defaultCanvas: CanvasState = {
    tema: { content: '', is_locked: false },
    problema: { content: '', is_locked: false },
    justificativa: { content: '', is_locked: false },
    objetivos: { geral: '', especificos: [] },
    metodologia: { tipo: '', instrumentos: [] },
}

interface ProjectStore {
    canvas: CanvasState
    chatMessages: ChatMessage[]
    isStreaming: boolean
    activeAlmas: Alma[]
    empiricalDocuments: string[]
    updateCanvas: (canvas: CanvasState) => void
    updateCanvasField: (field: string, value: unknown) => void
    setMessages: (msgs: ChatMessage[]) => void
    addMessage: (msg: ChatMessage) => void
    appendToLastMessage: (chunk: string) => void
    setStreaming: (v: boolean) => void
    setActiveAlmas: (almas: Alma[]) => void
    setEmpiricalDocuments: (docs: string[]) => void
    reset: () => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
    canvas: defaultCanvas,
    chatMessages: [],
    isStreaming: false,
    activeAlmas: [],
    empiricalDocuments: [],

    updateCanvas: (canvas) => set({ canvas }),
    updateCanvasField: (field, value) =>
        set((s) => ({ canvas: { ...s.canvas, [field]: value } })),
    setMessages: (msgs) => set({ chatMessages: msgs }),
    addMessage: (msg) => set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
    appendToLastMessage: (chunk) =>
        set((s) => {
            const msgs = [...s.chatMessages]
            if (msgs.length > 0) msgs[msgs.length - 1].content += chunk
            return { chatMessages: msgs }
        }),
    setStreaming: (v) => set({ isStreaming: v }),
    setActiveAlmas: (almas) =>
        set({ activeAlmas: almas }),
    setEmpiricalDocuments: (docs) => set({ empiricalDocuments: docs }),
    reset: () =>
        set({ canvas: defaultCanvas, chatMessages: [], isStreaming: false, empiricalDocuments: [] }),
}))
