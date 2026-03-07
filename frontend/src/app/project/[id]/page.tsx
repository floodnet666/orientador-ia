'use client'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { useProjectStore, ChatMessage } from '@/store/project'
import { chatApi, projectsApi, empiricalApi } from '@/lib/api'
import { ChatSocket, DebateCallbacks } from '@/lib/ws'
import CanvasPanel from '@/components/canvas/CanvasPanel'
import ChatWindow from '@/components/chat/ChatWindow'

export default function ProjectPage() {
    const { id } = useParams<{ id: string }>()
    const { setMessages, addMessage, appendToLastMessage, setStreaming, updateCanvas, setEmpiricalDocuments } = useProjectStore()
    const socketRef = useRef<ChatSocket | null>(null)
    const [projectTitle, setProjectTitle] = useState('')
    const [uploading, setUploading] = useState(false)

    const _dispatchDebate = (type: string, data: Record<string, unknown>) => {
        window.dispatchEvent(
            new CustomEvent('chat_debate_event', { detail: { type, data } })
        )
    }

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
            (msg) => console.error('WS Error:', msg),
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

    return (
        <main className="flex h-screen bg-slate-900 overflow-hidden">
            {/* Chat — left 60% */}
            <section className="flex-1 flex flex-col min-w-0 border-r border-white/10">
                <header className="px-6 py-4 border-b border-white/10 flex items-center gap-3">
                    <a href="/dashboard" className="text-slate-400 hover:text-white text-sm transition">← Projetos</a>
                    <span className="text-white/30">|</span>
                    <h1 className="text-white font-semibold truncate">{projectTitle || '...'}</h1>
                </header>
                <ChatWindow onSend={sendMessage} onUpload={handleUpload} isUploading={uploading} />
            </section>

            {/* Canvas — right 40% */}
            <section className="w-96 flex-shrink-0">
                <CanvasPanel projectId={id} />
            </section>
        </main>
    )
}
