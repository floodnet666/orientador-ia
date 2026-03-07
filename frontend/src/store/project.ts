import { create } from 'zustand'

export interface CanvasState {
    tema: { content: string; is_locked: boolean }
    problema: { content: string; is_locked: boolean }
    justificativa: { content: string; is_locked: boolean }
    objetivos: { geral: string; especificos: string[] }
    metodologia: { tipo: string; instrumentos: string[] }
}

export interface ChatMessage {
    id?: string
    role: 'user' | 'alma' | 'system'
    alma_name?: string | null
    content: string
    created_at?: string
}

export interface AlmaInfo {
    id: string
    name: string
    description: string
    alma_type: string
    personality_descriptor: string
    score: number
}

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
    activeAlmas: { theoretical: AlmaInfo | null; methodological: AlmaInfo | null }
    empiricalDocuments: string[]
    updateCanvas: (canvas: CanvasState) => void
    updateCanvasField: (field: string, value: unknown) => void
    setMessages: (msgs: ChatMessage[]) => void
    addMessage: (msg: ChatMessage) => void
    appendToLastMessage: (chunk: string) => void
    setStreaming: (v: boolean) => void
    setActiveAlmas: (theoretical: AlmaInfo | null, methodological: AlmaInfo | null) => void
    setEmpiricalDocuments: (docs: string[]) => void
    reset: () => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
    canvas: defaultCanvas,
    chatMessages: [],
    isStreaming: false,
    activeAlmas: { theoretical: null, methodological: null },
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
    setActiveAlmas: (theoretical, methodological) =>
        set({ activeAlmas: { theoretical, methodological } }),
    setEmpiricalDocuments: (docs) => set({ empiricalDocuments: docs }),
    reset: () =>
        set({ canvas: defaultCanvas, chatMessages: [], isStreaming: false, empiricalDocuments: [] }),
}))
