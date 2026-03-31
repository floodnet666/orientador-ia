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

interface AlmaCatalogCard {
    id: string
    name: string
    description: string
    alma_type: string
    personality_descriptor: string
}

export default function MatchPage() {
    const router = useRouter()
    const { id } = useParams<{ id: string }>()

    const [rawIdea, setRawIdea] = useState('')
    const [results, setResults] = useState<MatchResult | null>(null)
    const [selectedIds, setSelectedIds] = useState<string[]>([])
    const [loading, setLoading] = useState(false)
    const [confirming, setConfirming] = useState(false)
    const [error, setError] = useState('')
    const [catalog, setCatalog] = useState<AlmaCatalogCard[]>([])

    useEffect(() => {
        async function fetchCatalog() {
            try {
                const res = await projectsApi.getAlmas() as AlmaCatalogCard[]
                setCatalog(res)
            } catch (e) {
                console.error('Failed to fetch catalog:', e)
            }
        }
        fetchCatalog()
    }, [])

    async function handleMatch() {
        setLoading(true)
        setError('')
        try {
            const res = await projectsApi.match(id, rawIdea) as MatchResult
            setResults(res)
            // Auto-seleciona as melhores sugestões iniciais
            const initialIds = [
                ...(res.theoretical.length > 0 ? [res.theoretical[0].id] : []),
                ...(res.methodological.length > 0 ? [res.methodological[0].id] : [])
            ]
            setSelectedIds(initialIds)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Match failed')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (id) {
            projectsApi.get(id).then(project => {
                if (project.soul_ids && project.soul_ids.length > 0) {
                    setSelectedIds(project.soul_ids)
                }
            }).catch(console.error)
        }
    }, [id])

    async function handleConfirm() {
        if (selectedIds.length === 0) return
        setConfirming(true)
        try {
            await projectsApi.selectAlmas(id, {
                alma_ids: selectedIds
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

                {results ? (
                    <div className="space-y-6">
                        {[
                            { key: 'theoretical' as const, label: 'Sugestões Teóricas', items: results.theoretical },
                            { key: 'methodological' as const, label: 'Sugestões Metodológicas', items: results.methodological },
                        ].map(({ key, label, items }) => (
                            <div key={key}>
                                <h2 className="text-lg font-semibold text-white mb-3">{label}</h2>
                                {items.length > 0 ? (
                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                        {items.map((alma) => (
                                            <button
                                                key={alma.id}
                                                id={`alma-${alma.id}`}
                                                onClick={() => {
                                                    setSelectedIds(prev => 
                                                        prev.includes(alma.id) ? prev.filter(x => x !== alma.id) : [...prev, alma.id]
                                                    )
                                                }}
                                                className={`text-left p-4 rounded-xl border transition relative group ${selectedIds.includes(alma.id)
                                                    ? 'border-indigo-500 bg-indigo-600/20 ring-1 ring-indigo-500/50'
                                                    : 'border-white/10 bg-white/5 hover:bg-white/10'
                                                    }`}
                                            >
                                                {selectedIds.includes(alma.id) && (
                                                    <div className="absolute -top-2 -right-2 bg-indigo-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-[10px] shadow-lg animate-in zoom-in duration-200">
                                                        ✓
                                                    </div>
                                                )}
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-white font-semibold text-sm">{alma.name}</span>
                                                    {selectedIds.includes(alma.id) ? (
                                                        <span className="text-[9px] bg-indigo-500 text-white px-1.5 py-0.5 rounded-md font-bold uppercase tracking-tighter">Conselheiro</span>
                                                    ) : (
                                                        <span className="text-xs text-slate-400">{(alma.score * 100).toFixed(0)}%</span>
                                                    )}
                                                </div>
                                                <p className="text-slate-400 text-xs leading-relaxed line-clamp-2">{alma.description}</p>
                                                <p className="text-indigo-400 text-xs mt-2 italic">{alma.personality_descriptor}</p>
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-slate-500 text-sm">Nenhuma sugestão encontrada.</p>
                                )}
                            </div>
                        ))}
                    </div>
                ) : catalog.length > 0 ? (
                    <div className="space-y-6">
                        {[
                            { key: 'theoretical' as const, label: 'Almas Teóricas (Catálogo)', items: catalog.filter(a => a.alma_type === 'THEORETICAL') },
                            { key: 'methodological' as const, label: 'Avatares Metodológicos (Catálogo)', items: catalog.filter(a => a.alma_type === 'METHODOLOGICAL') },
                        ].map(({ key, label, items }) => (
                            <div key={key}>
                                <h2 className="text-lg font-semibold text-white mb-3">{label}</h2>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {items.map((alma) => (
                                        <button
                                            key={alma.id}
                                            id={`catalogo-${alma.id}`}
                                            onClick={() => {
                                                setSelectedIds(prev => 
                                                    prev.includes(alma.id) ? prev.filter(x => x !== alma.id) : [...prev, alma.id]
                                                )
                                            }}
                                            className={`text-left p-4 rounded-xl border transition relative group ${selectedIds.includes(alma.id)
                                                ? 'border-indigo-500 bg-indigo-600/20 ring-1 ring-indigo-500/50'
                                                : 'border-white/10 bg-white/5 hover:bg-white/10'
                                                }`}
                                        >
                                            {selectedIds.includes(alma.id) && (
                                                <div className="absolute -top-2 -right-2 bg-indigo-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-[10px] shadow-lg animate-in zoom-in duration-200">
                                                    ✓
                                                </div>
                                            )}
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-white font-semibold text-sm">{alma.name}</span>
                                            </div>
                                            <p className="text-slate-400 text-xs leading-relaxed line-clamp-2">{alma.description}</p>
                                            <p className="text-indigo-400 text-xs mt-2 italic truncate">{alma.personality_descriptor}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : null}

                {(results || catalog.length > 0) && (
                    <div className="mt-8">
                        <button
                            id="confirm-almas-button"
                            onClick={handleConfirm}
                            disabled={confirming || selectedIds.length === 0}
                            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl shadow-lg shadow-indigo-500/20 transition flex items-center justify-center gap-2"
                        >
                            {confirming ? 'A confirmar...' : `Confirmar Equipe (${selectedIds.length} Almas) e Abrir Ateliê`}
                        </button>
                    </div>
                )}
            </div>
        </main>
    )
}
