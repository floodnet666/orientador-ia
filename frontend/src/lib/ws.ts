/**
 * ChatSocket — WebSocket client.
 * Handles both standard chat events and debate mode events.
 */
import { CanvasState } from '@/store/project'
import { ChatEventSchema, ChatEvent } from './contracts/chat-events'
import { components } from '@/types/api-schema'


const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
const MAX_RECONNECTS = 10
const RECONNECT_DELAY_MS = 2000

export type DebatePanel = Record<string, {
    name: string;
    rationale?: string;
    angle?: string;
}>;

export interface DebateCallbacks {
    onSystemStatus: (message: string) => void
    onPanelSelected: (panel: DebatePanel, almas: any[]) => void
    onDebateTurnStart: (role: string, almaName: string) => void
    onDebateChunk: (role: string, content: string) => void
    onDebateTurnEnd: (role: string, alma_name: string, content: string) => void
    onDebateQuestion: (tensions: string[], consensus: string[], question: string, recommendations?: string[]) => void
    onDebateManifest: (almas: Record<string, any>) => void
}

export class ChatSocket {
    private ws: WebSocket | null = null
    private queue: string[] = []
    private reconnectCount = 0
    private closed = false
    private heartbeatTimer: any = null

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
            if (window.location.port === '3000') {
                // Bypass Next.js proxy (3000) for WS upgrade support ONLY in local dev
                baseUrl = `${protocol}//${window.location.hostname}:8000`
            } else {
                // Use standard host (Proxy 8080 or Ngrok)
                baseUrl = `${protocol}//${window.location.host}`
            }
        }
        baseUrl = baseUrl || 'ws://localhost:8000'



        const url = `${baseUrl}/api/chat/${this.projectId}/ws?token=${this.token}`
        console.log(`[WS] Connecting to ${url}`)
        this.ws = new WebSocket(url)

        this.ws.onopen = (evt) => {
            this.reconnectCount = 0
            console.log('[WS] OPEN (Event:', evt, ') — flushing queue:', this.queue.length, 'msgs')
            
            // Start heartbeat
            this._startHeartbeat()

            const pending = [...this.queue]
            this.queue = []
            pending.forEach(msg => this.ws!.send(msg))
        }

        this.ws.onmessage = (event) => {
            try {
                const rawData = JSON.parse(event.data)
                const result = ChatEventSchema.safeParse(rawData)
                
                if (!result.success) {
                    console.error('[WS] Contract Violation Details:', {
                        error: result.error.format(),
                        rawData: rawData
                    })
                    return
                }

                const data = result.data
                const dc = this.debateCallbacks

                switch (data.type) {
                    case 'connected':
                        console.log('[WS] Connected as:', data.user)
                        break
                    case 'chunk':
                        this.onChunk(data.text)
                        break
                    case 'canvas_update':
                        this.onCanvasUpdate(data.canvas)
                        break
                    case 'done':
                        this.onDone()
                        break
                    case 'guardrail_block':
                        this.onGuardrailBlock(data.text)
                        break
                    case 'error':
                        this.onError(data.message)
                        break
                    case 'panel_selected':
                        dc?.onPanelSelected(data.panel as DebatePanel, data.almas)
                        break;
                    case 'debate_turn_start':
                        dc?.onDebateTurnStart(data.role, data.alma_name)
                        break
                    case 'debate_chunk':
                        dc?.onDebateChunk(data.role, data.content)
                        break
                    case 'debate_question':
                        dc?.onDebateQuestion(
                            data.data.tensions,
                            data.data.consensus,
                            data.data.question,
                            data.data.recommendations
                        )
                        break
                    case 'debate_turn_end':
                        dc?.onDebateTurnEnd(data.role, data.alma_name, data.content || '')
                        break
                    case 'debate_manifest':
                        dc?.onDebateManifest(data.almas)
                        break
                    case 'pong':
                        console.debug('[WS] Pong received')
                        break
                    case 'ping':
                        // If backend ever pings us
                        break
                }
            } catch (err) {
                console.error('[WS] Parse Error:', err)
            }
        }

        this.ws.onerror = (evt: any) => {
            console.error('[WS] ERROR EVENT DETAILED:', {
                url: this.ws?.url,
                readyState: this.ws?.readyState,
                event: evt,
                message: evt.message || 'Check network / CORS'
            })
            this.onError('WebSocket connection error')
        }

        this.ws.onclose = (evt) => {
            console.warn('[WS] CLOSED code=', evt.code, 'reason=', evt.reason, 'wasClean=', evt.wasClean)
            this._stopHeartbeat()

            if (evt.code === 1006 || evt.code === 1001) {
                console.info('[WS] Network interruption or Proxy timeout detected.')
            }
            if (!this.closed && this.reconnectCount < MAX_RECONNECTS) {
                this.reconnectCount++
                const delay = RECONNECT_DELAY_MS * Math.min(this.reconnectCount, 5)
                console.log(`[WS] Reconnecting attempt ${this.reconnectCount}/${MAX_RECONNECTS} in ${delay}ms`)
                setTimeout(() => this._open(), delay)
            } else if (!this.closed) {
                this.onError('Conexão perdida. Por favor, recarregue a página se o problema persistir.')
            }
        }
    }

    private _startHeartbeat() {
        this._stopHeartbeat()
        console.debug('[WS] Starting Heartbeat (15s)')
        this.heartbeatTimer = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                console.debug('[WS] Sending PING')
                this.ws.send(JSON.stringify({ type: 'ping' }))
            } else {
                console.warn('[WS] Cannot send PING, state=', this.ws?.readyState)
            }
        }, 15000)
    }

    private _stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer)
            this.heartbeatTimer = null
        }
    }
    sendMessage(content: string) {
        const payload = JSON.stringify({ type: 'message', content })
        if (this.ws?.readyState === WebSocket.OPEN) {
            console.log('[WS] SEND:', content.slice(0, 60))
            this.ws.send(payload)
        } else {
            console.warn('[WS] CANNOT SEND - READYSTATE:', this.ws?.readyState, ' - QUEUING')
            this.queue.push(payload)
            // Se estiver fechado ou fechando, tenta reabrir
            if (this.ws?.readyState === WebSocket.CLOSED || this.ws?.readyState === WebSocket.CLOSING) {
                this._open()
            }
        }
    }

    disconnect() {
        this.closed = true
        this.queue = []
        this.ws?.close()
    }
}
