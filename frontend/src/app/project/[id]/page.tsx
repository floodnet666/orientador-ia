'use client'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { useProjectStore, ChatMessage } from '@/store/project'
import { chatApi, projectsApi, empiricalApi } from '@/lib/api'
import { ChatSocket, DebateCallbacks } from '@/lib/ws'
import CanvasPanel from '@/components/canvas/CanvasPanel'
import ChatWindow from '@/components/chat/ChatWindow'
import { useHelp } from '@/store/HelpContext'
import HelpTooltip from '@/components/shared/HelpTooltip'

export default function ProjectPage() {
    const { id } = useParams<{ id: string }>()
    const { setMessages, addMessage, appendToLastMessage, setStreaming, updateCanvas, setEmpiricalDocuments, setActiveAlmas } = useProjectStore()
    const socketRef = useRef<ChatSocket | null>(null)
    const [projectTitle, setProjectTitle] = useState('')
    const [uploading, setUploading] = useState(false)
    const { isHelpModeActive, toggleHelpMode } = useHelp()

    const _dispatchDebate = (type: string, data: Record<string, unknown>) => {
        window.dispatchEvent(
            new CustomEvent('chat_debate_event', { detail: { type, data } })
        )
    }

    useEffect(() => {
        if (id) {
          (window as any).activeProjectId = id;
        }
        return () => { (window as any).activeProjectId = null; };
    }, [id]);

    useEffect(() => {
        const token = localStorage.getItem('token')
        if (!token || !id) return

        Promise.all([
            projectsApi.get(id),
            chatApi.history(id),
            projectsApi.getCanvas(id),
            empiricalApi.list(id),
            projectsApi.getAlmas(), // Pega o catálogo para resolver os nomes/roles
        ]).then(([project, history, canvas, docs, allAlmas]) => {
            const p = project as any
            setProjectTitle(p.title as string)
            setMessages(history as ChatMessage[])
            updateCanvas(canvas as Parameters<typeof updateCanvas>[0])
            setEmpiricalDocuments(docs as string[])
            
            // Use hydrated active almas directly from backend response
            if (p.active_almas) {
                setActiveAlmas(p.active_almas)
            }
        }).catch(console.error)

        // Debate callbacks — dispatch CustomEvents consumed by ChatWindow
        const debateCallbacks: DebateCallbacks = {
            onSystemStatus: (message) => _dispatchDebate('system_status', { message }),
            onPanelSelected: (panel, almas) => _dispatchDebate('panel_selected', { panel, almas }),
            onDebateTurnStart: (role, almaName) => {
                _dispatchDebate('debate_turn_start', { role, almaName })
                setStreaming(true)
            },
            onDebateChunk: (role, content) =>
                _dispatchDebate('debate_chunk', { role, content }),
            onDebateTurnEnd: (role, almaName, content) =>
                _dispatchDebate('debate_turn_end', { role, almaName, content }),
            onDebateQuestion: (tensions, consensus, question, recommendations) => {
                _dispatchDebate('debate_question', { tensions, consensus, question, recommendations })
                _dispatchDebate('debate_done', {})
                setStreaming(false)
            },
            onDebateManifest: (almas) => _dispatchDebate('debate_manifest', almas),
        }

        const socket = new ChatSocket()
        socketRef.current = socket
        socket.connect(
            id,
            token,
            (chunk) => appendToLastMessage(chunk),
            (canvas) => updateCanvas(canvas),
            () => {
                setStreaming(false)
                _dispatchDebate('debate_done', {}) // Fail-safe: ensure UI unlocks when streaming ends
            },
            (text) => {
                addMessage({ role: 'system', content: text })
                setStreaming(false)
            },
            (msg) => {
                console.error('WS Error:', msg)
                setStreaming(false)
                _dispatchDebate('debate_done', {}) // Safety reset for debate UI
            },
            debateCallbacks,
        )

        return () => {
            socket.disconnect()
        }
    }, [id])

    function sendMessage(content: string) {
        addMessage({ role: 'user', content })
        addMessage({ role: 'alma', content: '' })
        setStreaming(true)
        socketRef.current?.sendMessage(content)
    }

    async function handleUpload(file: File) {
        setUploading(true)
        try {
            await empiricalApi.upload(id as string, file)
            window.dispatchEvent(new CustomEvent('empirical_refresh'))
        } catch (e) {
            console.error('Upload failed', e)
        } finally {
            setUploading(false)
        }
    }

    const [chatWidth, setChatWidth] = useState(60) // percentage
    const isResizing = useRef(false)

    const startResizing = (e: React.MouseEvent) => {
        isResizing.current = true
        document.addEventListener('mousemove', handleMouseMove)
        document.addEventListener('mouseup', stopResizing)
        document.body.style.cursor = 'col-resize'
    }

    const stopResizing = () => {
        isResizing.current = false
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', stopResizing)
        document.body.style.cursor = 'default'
    }

    const handleMouseMove = (e: MouseEvent) => {
        if (!isResizing.current) return
        const newWidth = (e.clientX / window.innerWidth) * 100
        if (newWidth > 20 && newWidth < 80) {
            setChatWidth(newWidth)
        }
    }

    return (
        <main className="flex h-screen bg-slate-900 overflow-hidden">
            {/* Chat — Dynamic Width */}
            <section 
                className="flex flex-col min-w-0 border-r border-white/5 bg-slate-900/40 relative"
                style={{ width: `${chatWidth}%` }}
            >
                <header className="px-6 py-4 border-b border-white/10 flex items-center gap-3 bg-slate-900/80 backdrop-blur-md z-10">
                    <a href="/dashboard" id="back-to-dashboard" className="text-slate-400 hover:text-white transition p-2 rounded-lg bg-white/5 hover:bg-white/10" title="Voltar ao Dashboard">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                    </a>
                    <span className="text-white/10">|</span>
                    <a href={`/project/${id}/match`} id="return-to-matchmaker" className="text-slate-400 hover:text-white text-[11px] font-bold uppercase tracking-widest transition flex items-center gap-1.5 px-3 py-1 rounded-full border border-white/5 hover:border-indigo-500/50 hover:bg-indigo-500/10">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        Equipe de Almas
                    </a>
                    <span className="text-white/10">|</span>
                    <h1 className="text-white font-medium truncate tracking-tight flex-1">{projectTitle || 'Carregando projeto...'}</h1>
                    <button
                        onClick={toggleHelpMode}
                        className={`p-1.5 rounded-lg transition-colors text-sm ${isHelpModeActive ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white bg-white/5'}`}
                        title="Modo Ajuda"
                    >
                        ⁉️ Ajuda
                    </button>
                </header>
                <div className="flex-1 overflow-hidden flex flex-col">
                    <HelpTooltip content="Aqui pode conversar com as suas Almas. O Maestro orquestra quem responde com base na sua dúvida." position="right">
                        <ChatWindow onSend={sendMessage} onUpload={handleUpload} isUploading={uploading} />
                    </HelpTooltip>
                </div>
            </section>

            {/* Resizable Divider Handle */}
            <div
                onMouseDown={startResizing}
                className="w-1.5 hover:w-2 bg-transparent hover:bg-indigo-500/30 active:bg-indigo-500/50 cursor-col-resize transition-all duration-200 z-20 flex items-center justify-center group"
            >
                <div className="w-[1px] h-8 bg-white/10 group-hover:bg-indigo-400/50 rounded-full" />
            </div>

            {/* Canvas — Remaining Width */}
            <section className="flex-1 min-w-0 bg-slate-950/20">
                <HelpTooltip content="O Whiteboard visualiza o progresso acadêmico. O Maestro atualiza estes campos conforme discutem no chat." position="left">
                    <CanvasPanel projectId={id} />
                </HelpTooltip>
            </section>
        </main>
    )
}
