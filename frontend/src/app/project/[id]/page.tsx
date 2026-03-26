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
    const { setMessages, addMessage, appendToLastMessage, setStreaming, updateCanvas, setEmpiricalDocuments } = useProjectStore()
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
        ]).then(([project, history, canvas, docs]) => {
            const p = project as Record<string, unknown>
            setProjectTitle(p.title as string)
            setMessages(history as ChatMessage[])
            updateCanvas(canvas as Parameters<typeof updateCanvas>[0])
            setEmpiricalDocuments(docs as string[])
        }).catch(console.error)

        // Debate callbacks — dispatch CustomEvents consumed by ChatWindow
        const debateCallbacks: DebateCallbacks = {
            onSystemStatus: (message) => _dispatchDebate('system_status', { message }),
            onPanelSelected: (panel) => _dispatchDebate('panel_selected', { panel }),
            onDebateTurnStart: (role, almaName, turn) => {
                _dispatchDebate('debate_turn_start', { role, almaName, turn })
                setStreaming(true)
            },
            onDebateChunk: (role, almaName, content, turn) =>
                _dispatchDebate('debate_chunk', { role, almaName, content, turn }),
            onDebateTurnEnd: (role, almaName, content, turn) =>
                _dispatchDebate('debate_turn_end', { role, almaName, content, turn }),
            onDebateQuestion: (tensions, consensus, question) => {
                _dispatchDebate('debate_question', { tensions, consensus, question })
                _dispatchDebate('debate_done', {})
                setStreaming(false)
            },
        }

        const socket = new ChatSocket()
        socketRef.current = socket
        socket.connect(
            id,
            token,
            (chunk) => appendToLastMessage(chunk),
            (canvas) => updateCanvas(canvas),
            () => setStreaming(false),
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
        <main className="flex h-screen bg-slate-900 overflow-hidden select-none">
            {/* Chat — Dynamic Width */}
            <section 
                className="flex flex-col min-w-0 border-r border-white/5 bg-slate-900/40 relative"
                style={{ width: `${chatWidth}%` }}
            >
                <header className="px-6 py-4 border-b border-white/10 flex items-center gap-3 bg-slate-900/80 backdrop-blur-md z-10">
                    <a href="/dashboard" className="text-slate-400 hover:text-white text-sm transition flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                        Projetos
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
