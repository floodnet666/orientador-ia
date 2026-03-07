'use client'
import { useState } from 'react'
import { almasApi } from '@/lib/api'

interface Props {
    isOpen: boolean
    onClose: () => void
    onCreated: () => void
}

export default function GenesisModal({ isOpen, onClose, onCreated }: Props) {
    const [prompt, setPrompt] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    if (!isOpen) return null

    const handleCreate = async () => {
        if (!prompt.trim()) return
        setLoading(true)
        setError(null)
        try {
            await almasApi.genesis(prompt)
            onCreated()
            onClose()
            setPrompt('')
        } catch (err: any) {
            setError(err.message || 'Erro ao criar Alma')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="bg-slate-900 border border-white/10 w-full max-w-lg rounded-3xl overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-300">
                <header className="p-6 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-indigo-500/10 to-transparent">
                    <div>
                        <h2 className="text-xl font-bold text-white">Agente Génesis</h2>
                        <p className="text-slate-400 text-xs mt-1">Criação de Alma Personalizada via Prompt</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </header>

                <div className="p-6 space-y-4">
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-widest px-1">
                            Descrição da Alma
                        </label>
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Ex: Crie uma Alma focada em IA na Saúde, com postura crítica sobre privacidade de dados e conhecimento profundo em redes neuronais."
                            className="w-full h-40 bg-white/5 border border-white/10 rounded-2xl p-4 text-white text-sm focus:outline-none focus:border-indigo-500/50 transition resize-none placeholder:text-slate-600"
                            disabled={loading}
                        />
                    </div>

                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs p-3 rounded-xl flex items-center gap-2">
                            <span>⚠️ {error}</span>
                        </div>
                    )}
                </div>

                <footer className="p-6 bg-white/5 border-t border-white/10 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-5 py-2.5 text-sm font-medium text-slate-400 hover:text-white transition"
                        disabled={loading}
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={loading || !prompt.trim()}
                        className={`
                            px-6 py-2.5 rounded-xl text-sm font-bold text-white transition shadow-lg
                            ${loading || !prompt.trim() ? 'bg-slate-700 cursor-not-allowed opacity-50' : 'bg-indigo-600 hover:bg-indigo-500 active:scale-95 shadow-indigo-500/20'}
                        `}
                    >
                        {loading ? 'A gerar Alma...' : 'Gerar Alma'}
                    </button>
                </footer>
            </div>
        </div>
    )
}
