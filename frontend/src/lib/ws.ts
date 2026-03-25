/**
 * ChatSocket — WebSocket client.
 * Handles both standard chat events and debate mode events.
 */
import { CanvasState } from '@/store/project'

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
const MAX_RECONNECTS = 3
const RECONNECT_DELAY_MS = 1500

export interface DebatePanel {
    PRIMARIA: { name: string; rationale?: string }
    COMPLEMENTAR: { name: string; rationale?: string }
    ANTAGONISTA: { name: string; angle?: string }
    METODOLOGICA: { name: string }
}

export interface DebateCallbacks {
    onSystemStatus: (message: string) => void
    onPanelSelected: (panel: DebatePanel) => void
    onDebateTurnStart: (role: string, almaName: string, turn: number) => void
    onDebateChunk: (role: string, almaName: string, content: string, turn: number) => void
    onDebateTurnEnd: (role: string, almaName: string, content: string, turn: number) => void
    onDebateQuestion: (tensions: string[], consensus: string[], question: string) => void
}

export class ChatSocket {
    private ws: WebSocket | null = null
    private queue: string[] = []
    private reconnectCount = 0
    private closed = false

    private projectId = ''
    private token = ''
    private onChunk: (text: string) => void = () => { }
    private onCanvasUpdate: (canvas: CanvasState) => void = () => { }
    private onDone: () => void = () => { }
    private onGuardrailBlock: (text: string) => void = () => { }
    private onError: (msg: string) => void = () => { }
    private debateCallbacks: DebateCallbacks | null = null

    connect(
        projectId: string,
        token: string,
        onChunk: (text: string) => void,
        onCanvasUpdate: (canvas: CanvasState) => void,
        onDone: () => void,
        onGuardrailBlock: (text: string) => void,
        onError: (msg: string) => void,
        debateCallbacks?: DebateCallbacks,
    ) {
        this.projectId = projectId
        this.token = token
        this.onChunk = onChunk
        this.onCanvasUpdate = onCanvasUpdate
        this.onDone = onDone
        this.onGuardrailBlock = onGuardrailBlock
        this.onError = onError
        this.debateCallbacks = debateCallbacks ?? null
        this.closed = false
        this._open()
        return this
    }

    private _open() {
        let baseUrl = process.env.NEXT_PUBLIC_WS_URL
        if (!baseUrl && typeof window !== 'undefined') {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            // Bypass Next.js proxy (3000) for WS upgrade support
            const host = window.location.hostname
            baseUrl = `${protocol}//${host}:8000`
        }
        baseUrl = baseUrl || 'ws://localhost:8000'


        const url = `${baseUrl}/api/chat/${this.projectId}/ws?token=${this.token}`
        console.log(`[WS] Connecting to ${url}`)
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
            this.reconnectCount = 0
            console.log('[WS] OPEN — flushing queue:', this.queue.length, 'msgs')
            const pending = [...this.queue]
            this.queue = []
            pending.forEach(msg => this.ws!.send(msg))
        }

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            const dc = this.debateCallbacks

            switch (data.type) {
                // ── Standard events ───────────────────────────────────────────
                case 'chunk':
                    this.onChunk(data.text)
                    break
                case 'action':
                    window.dispatchEvent(
                        new CustomEvent('chat_action_event', { detail: data.token })
                    )
                    break
                case 'canvas_update':
                    this.onCanvasUpdate(data.canvas || data.updates)
                    break
                case 'done':
                    this.onDone()
                    break
                case 'guardrail_block':
                    this.onGuardrailBlock(data.text || data.content)
                    break
                case 'error':
                    this.onError(data.message)
                    break

                // ── Debate events ─────────────────────────────────────────────
                case 'system_status':
                    dc?.onSystemStatus(data.message)
                    break
                case 'panel_selected':
                    dc?.onPanelSelected(data.panel)
                    break
                case 'debate_turn_start':
                    dc?.onDebateTurnStart(data.role, data.alma_name, data.turn_number)
                    break
                case 'debate_chunk':
                    dc?.onDebateChunk(data.role, data.alma_name, data.content, data.turn_number)
                    break
                case 'debate_turn_end':
                    dc?.onDebateTurnEnd(data.role, data.alma_name, data.content, data.turn_number)
                    break
                case 'debate_question':
                    dc?.onDebateQuestion(data.tensions, data.consensus, data.question)
                    break
                case 'debate_complete':
                    // Internal — no UI action needed
                    break
                default:
                    console.log('[WS] Unknown event type:', data.type)
            }
        }

        this.ws.onerror = (evt) => {
            console.error('[WS] ERROR', evt)
            this.onError('WebSocket connection error')
        }

        this.ws.onclose = (evt) => {
            console.warn('[WS] CLOSED code=', evt.code, 'reason=', evt.reason)
            if (!this.closed && this.reconnectCount < MAX_RECONNECTS) {
                this.reconnectCount++
                console.log(`[WS] Reconnecting attempt ${this.reconnectCount}/${MAX_RECONNECTS}`)
                setTimeout(() => this._open(), RECONNECT_DELAY_MS)
            } else if (!this.closed) {
                this.onError('WebSocket disconnected after multiple attempts')
            }
        }
    }

    sendMessage(content: string) {
        const payload = JSON.stringify({ type: 'message', content })
        if (this.ws?.readyState === WebSocket.OPEN) {
            console.log('[WS] SEND:', content.slice(0, 60))
            this.ws.send(payload)
        } else {
            console.warn('[WS] Not open yet (state=', this.ws?.readyState, ') — queuing')
            this.queue.push(payload)
        }
    }

    disconnect() {
        this.closed = true
        this.queue = []
        this.ws?.close()
    }
}
