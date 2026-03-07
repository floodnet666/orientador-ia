'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { projectsApi } from '@/lib/api'

interface AlmaSuggestion {
    id: string
    name: string
    description: string
    alma_type: string
    personality_descriptor: string
    score: number
}

interface MatchResult {
    theoretical: AlmaSuggestion[]
    methodological: AlmaSuggestion[]
}

export default function MatchPage() {
    const router = useRouter()
    const { id } = useParams<{ id: string }>()
    const [rawIdea, setRawIdea] = useState('')
    const [results, setResults] = useState<MatchResult | null>(null)
    const [selected, setSelected] = useState<{ theoretical: string; methodological: string }>({
        theoretical: '',
        methodological: '',
    })
    const [loading, setLoading] = useState(false)
    const [confirming, setConfirming] = useState(false)
    const [error, setError] = useState('')

    async function handleMatch() {
        setLoading(true)
        setError('')
        try {
            const res = await projectsApi.match(id, rawIdea) as MatchResult
            setResults(res)
            if (res.theoretical.length > 0) setSelected(s => ({ ...s, theoretical: res.theoretical[0].id }))
            if (res.methodological.length > 0) setSelected(s => ({ ...s, methodological: res.methodological[0].id }))
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Match failed')
        } finally {
            setLoading(false)
        }
    }

    async function handleConfirm() {
        if (!selected.theoretical || !selected.methodological) return
        setConfirming(true)
        try {
            await projectsApi.selectAlmas(id, {
                theoretical_alma_id: selected.theoretical,
                methodological_alma_id: selected.methodological,
            })
            router.push(`/project/${id}`)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Selection failed')
        } finally {
            setConfirming(false)
        }
    }

    return (
        <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 px-4 py-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-2">Selecionar Almas</h1>
                <p className="text-slate-400 mb-8">Descreva a sua ideia de investigação e o sistema sugerirá as Almas mais adequadas.</p>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
                    <label className="block text-sm text-slate-300 mb-2">A sua ideia de investigação</label>
                    <textarea
                        id="raw-idea"
                        rows={4}
                        value={rawIdea}
                        onChange={(e) => setRawIdea(e.target.value)}
                        placeholder="Descreva em texto livre o tema, contexto ou questão que quer investigar..."
                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400 resize-none transition"
                    />
                    {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
                    <button
                        id="match-button"
                        onClick={handleMatch}
                        disabled={loading || rawIdea.trim().length < 10}
                        className="mt-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold px-6 py-2.5 rounded-lg transition"
                    >
                        {loading ? 'A analisar...' : 'Encontrar Almas'}
                    </button>
                </div>

                {results && (
                    <div className="space-y-6">
                        {[
                            { key: 'theoretical' as const, label: 'Almas Teóricas', items: results.theoretical },
                            { key: 'methodological' as const, label: 'Avatares Metodológicos', items: results.methodological },
                        ].map(({ key, label, items }) => (
                            <div key={key}>
                                <h2 className="text-lg font-semibold text-white mb-3">{label}</h2>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                    {items.map((alma) => (
                                        <button
                                            key={alma.id}
                                            id={`alma-${alma.id}`}
                                            onClick={() => setSelected(s => ({ ...s, [key]: alma.id }))}
                                            className={`text-left p-4 rounded-xl border transition ${selected[key] === alma.id
                                                    ? 'border-indigo-500 bg-indigo-600/20'
                                                    : 'border-white/10 bg-white/5 hover:bg-white/10'
                                                }`}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-white font-semibold text-sm">{alma.name}</span>
                                                <span className="text-xs text-slate-400">{(alma.score * 100).toFixed(0)}%</span>
                                            </div>
                                            <p className="text-slate-400 text-xs leading-relaxed">{alma.description.slice(0, 120)}...</p>
                                            <p className="text-indigo-400 text-xs mt-2 italic">{alma.personality_descriptor}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}

                        <button
                            id="confirm-almas-button"
                            onClick={handleConfirm}
                            disabled={confirming || !selected.theoretical || !selected.methodological}
                            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition"
                        >
                            {confirming ? 'A confirmar...' : 'Confirmar Almas e Abrir Ateliê'}
                        </button>
                    </div>
                )}
            </div>
        </main>
    )
}
