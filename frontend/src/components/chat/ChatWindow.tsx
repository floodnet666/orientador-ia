'use client'
import { useRef, useEffect, useState } from 'react'
import { useProjectStore } from '@/store/project'
import DebatePanel from './DebatePanel'

interface Props {
    onSend: (message: string) => void
    onUpload?: (file: File) => void
    isUploading?: boolean
}

type DebateRole = 'PRIMARIA' | 'COMPLEMENTAR' | 'ANTAGONISTA' | 'METODOLOGICA'

interface DebateTurn {
    role: DebateRole
    almaName: string
    content: string
    isStreaming: boolean
}

interface DebateQuestionData {
    tensions: string[]
    consensus: string[]
    question: string
}

interface ActivePanel {
    PRIMARIA: { name: string; rationale?: string }
    COMPLEMENTAR: { name: string; rationale?: string }
    ANTAGONISTA: { name: string; angle?: string }
    METODOLOGICA: { name: string }
}

const ROLE_STYLES: Record<DebateRole, string> = {
    PRIMARIA: 'border-violet-500/40 bg-violet-500/10',
    COMPLEMENTAR: 'border-cyan-500/40 bg-cyan-500/10',
    ANTAGONISTA: 'border-rose-500/40 bg-rose-500/10',
    METODOLOGICA: 'border-amber-500/40 bg-amber-500/10',
}

const ROLE_NAME_STYLES: Record<DebateRole, string> = {
    PRIMARIA: 'text-violet-400',
    COMPLEMENTAR: 'text-cyan-400',
    ANTAGONISTA: 'text-rose-400',
    METODOLOGICA: 'text-amber-400',
}

const ROLE_LABELS: Record<DebateRole, string> = {
    PRIMARIA: 'Primária',
    COMPLEMENTAR: 'Complementar',
    ANTAGONISTA: 'Antagonista',
    METODOLOGICA: 'Metodológica',
}

const CHAT_ROLE_STYLES = {
    user: 'bg-indigo-600/20 border-indigo-500/30 ml-8',
    alma: 'bg-white/5 border-white/10 mr-8',
    system: 'bg-yellow-900/20 border-yellow-500/30 mx-4 text-center',
}

export default function ChatWindow({ onSend, onUpload, isUploading }: Props) {
    const { chatMessages, isStreaming } = useProjectStore()
    const [input, setInput] = useState('')
    const bottomRef = useRef<HTMLDivElement>(null)

    function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0]
        if (file && onUpload) {
            onUpload(file)
            e.target.value = ''
        }
    }


    // Debate state (local — not in Zustand store)
    const [debatePanel, setDebatePanel] = useState<ActivePanel | null>(null)
    const [activeDebateRole, setActiveDebateRole] = useState<DebateRole | null>(null)
    const [debateTurns, setDebateTurns] = useState<DebateTurn[]>([])
    const [debateQuestion, setDebateQuestion] = useState<DebateQuestionData | null>(null)
    const [systemStatus, setSystemStatus] = useState<string | null>(null)
    const [isDebating, setIsDebating] = useState(false)

    // Expose debate callbacks so project page can wire them up
    // We use a module-level event bus pattern via CustomEvent
    useEffect(() => {
        const handleDebateEvent = (e: CustomEvent) => {
            const { type, data } = e.detail
            switch (type) {
                case 'system_status':
                    setSystemStatus(data.message)
                    setIsDebating(true)
                    break
                case 'panel_selected':
                    setDebatePanel(data.panel)
                    setDebateTurns([])
                    setDebateQuestion(null)
                    break
                case 'debate_turn_start':
                    setActiveDebateRole(data.role as DebateRole)
                    setDebateTurns(prev => [
                        ...prev,
                        { role: data.role, almaName: data.almaName, content: '', isStreaming: true }
                    ])
                    break
                case 'debate_chunk':
                    setDebateTurns(prev => {
                        const updated = [...prev]
                        const last = updated[updated.length - 1]
                        if (last && last.role === data.role) {
                            updated[updated.length - 1] = { ...last, content: last.content + data.content }
                        }
                        return updated
                    })
                    break
                case 'debate_turn_end':
                    setActiveDebateRole(null)
                    setDebateTurns(prev => {
                        const updated = [...prev]
                        const last = updated[updated.length - 1]
                        if (last) updated[updated.length - 1] = { ...last, isStreaming: false }
                        return updated
                    })
                    break
                case 'debate_question':
                    setDebateQuestion(data)
                    setIsDebating(false)
                    setSystemStatus(null)
                    break
                case 'debate_done':
                    setIsDebating(false)
                    setActiveDebateRole(null)
                    break
            }
        }

        window.addEventListener('chat_debate_event', handleDebateEvent as EventListener)
        return () => window.removeEventListener('chat_debate_event', handleDebateEvent as EventListener)
    }, [])

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [chatMessages, debateTurns, debateQuestion])

    function handleSend() {
        if (!input.trim() || isStreaming || isDebating) return
        // Reset debate state when user sends a new message
        setDebatePanel(null)
        setDebateTurns([])
        setDebateQuestion(null)
        setSystemStatus(null)
        onSend(input.trim())
        setInput('')
    }

    function handleKey(e: React.KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const isBusy = isStreaming || isDebating

    return (
        <div className="flex flex-col flex-1 overflow-hidden">
            {/* Debate panel header */}
            {debatePanel && (
                <DebatePanel panel={debatePanel} activeRole={activeDebateRole} />
            )}

            {/* System status banner */}
            {systemStatus && (
                <div className="px-4 py-2 bg-indigo-900/30 border-b border-indigo-500/20 flex items-center gap-2">
                    <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
                    <p className="text-xs text-indigo-300">{systemStatus}</p>
                </div>
            )}

            {/* Message list */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                {chatMessages.length === 0 && debateTurns.length === 0 && (
                    <div className="text-center py-12">
                        <p className="text-slate-400">Comece o diálogo com as suas Almas.</p>
                        <p className="text-slate-500 text-sm mt-2">Descreva a sua questão de investigação.</p>
                        <p className="text-slate-600 text-xs mt-3">
                            💡 Dica: diga <em>"me ajude a desenvolver a justificativa"</em> para activar o debate entre Almas.
                        </p>
                    </div>
                )}

                {/* Standard messages */}
                {chatMessages.map((msg, i) => (
                    <div
                        key={i}
                        className={`rounded-xl border px-4 py-3 ${CHAT_ROLE_STYLES[msg.role as keyof typeof CHAT_ROLE_STYLES] || CHAT_ROLE_STYLES.system}`}
                    >
                        {msg.alma_name && (
                            <p className="text-xs text-indigo-400 font-semibold mb-1">{msg.alma_name}</p>
                        )}
                        <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    </div>
                ))}

                {/* Standard streaming indicator */}
                {isStreaming && !isDebating && (
                    <div className="flex gap-1 px-4 py-2">
                        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                )}

                {/* Debate turns */}
                {debateTurns.map((turn, i) => (
                    <div
                        key={`debate-${i}`}
                        className={`rounded-xl border px-4 py-3 mr-4 transition-all ${ROLE_STYLES[turn.role]}`}
                    >
                        <div className="flex items-center gap-2 mb-1.5">
                            <p className={`text-xs font-bold ${ROLE_NAME_STYLES[turn.role]}`}>
                                {turn.almaName}
                            </p>
                            <span className={`text-xs px-1.5 py-0.5 rounded border ${ROLE_NAME_STYLES[turn.role]} border-current opacity-60`}>
                                {ROLE_LABELS[turn.role]}
                            </span>
                            {turn.isStreaming && (
                                <span className="ml-auto flex gap-0.5">
                                    <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </span>
                            )}
                        </div>
                        <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">{turn.content}</p>
                    </div>
                ))}

                {/* Debate question card */}
                {debateQuestion && (
                    <div className="rounded-xl border border-white/20 bg-gradient-to-br from-slate-800 to-slate-900 px-5 py-4 mt-2">
                        <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-3">
                            Síntese do Debate
                        </p>
                        {debateQuestion.tensions.length > 0 && (
                            <div className="mb-3">
                                <p className="text-xs text-rose-400 font-semibold mb-1">⚡ Tensões em aberto</p>
                                <ul className="space-y-1">
                                    {debateQuestion.tensions.map((t, i) => (
                                        <li key={i} className="text-xs text-slate-300 pl-2 border-l border-rose-500/40">{t}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {debateQuestion.consensus.length > 0 && (
                            <div className="mb-3">
                                <p className="text-xs text-emerald-400 font-semibold mb-1">✓ Pontos de consenso</p>
                                <ul className="space-y-1">
                                    {debateQuestion.consensus.map((c, i) => (
                                        <li key={i} className="text-xs text-slate-300 pl-2 border-l border-emerald-500/40">{c}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        <div className="mt-3 pt-3 border-t border-white/10">
                            <p className="text-xs text-amber-400 font-semibold mb-1.5">❓ Pergunta para ti</p>
                            <p className="text-white text-sm font-medium leading-relaxed">
                                {debateQuestion.question}
                            </p>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Input area */}
            <div className="px-4 py-3 border-t border-white/10 bg-slate-900/50">
                <div className="relative flex items-end bg-white/5 border border-white/20 rounded-xl focus-within:border-indigo-500/50 focus-within:bg-white/10 transition-colors">
                    <textarea
                        id="chat-input"
                        rows={1}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKey}
                        disabled={isBusy}
                        placeholder={
                            isDebating
                                ? 'Aguardando o debate terminar...'
                                : 'Escreva a sua mensagem... (Enter para enviar)'
                        }
                        className="flex-1 bg-transparent px-4 py-3 pr-24 text-white text-sm placeholder-slate-500 focus:outline-none resize-none disabled:opacity-50 min-h-[48px] max-h-[120px]"
                    />

                    <div className="absolute right-2 bottom-2 flex items-center gap-1.5">
                        {onUpload && (
                            <label
                                className={`flex justify-center items-center w-8 h-8 rounded-lg transition cursor-pointer flex-shrink-0
                                    ${(isUploading || isBusy)
                                        ? 'bg-white/5 text-slate-500 cursor-not-allowed'
                                        : 'bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white border border-indigo-500/30'}
                                `}
                                title="Fazer upload de Documentos (PDF, TXT, CSV)"
                            >
                                {isUploading ? (
                                    <span className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                                ) : (
                                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                        <line x1="12" y1="5" x2="12" y2="19"></line>
                                        <line x1="5" y1="12" x2="19" y2="12"></line>
                                    </svg>
                                )}
                                <input type="file" className="hidden" accept=".pdf,.txt,.csv" onChange={handleFileUpload} disabled={isUploading || isBusy} />
                            </label>
                        )}
                        <button
                            id="send-button"
                            onClick={handleSend}
                            disabled={isBusy || !input.trim()}
                            className="flex justify-center items-center w-8 h-8 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/10 disabled:text-slate-500 text-white transition flex-shrink-0"
                            title="Enviar"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="12" y1="19" x2="12" y2="5"></line>
                                <polyline points="5 12 12 5 19 12"></polyline>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
