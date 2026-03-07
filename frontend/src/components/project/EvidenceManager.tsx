'use client'
import { useState, useEffect } from 'react'
import { useProjectStore } from '@/store/project'
import { empiricalApi } from '@/lib/api'

interface Props {
    projectId: string
}

export default function EvidenceManager({ projectId }: Props) {
    const { empiricalDocuments, setEmpiricalDocuments } = useProjectStore()
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchDocs = () => {
            if (projectId) {
                empiricalApi.list(projectId)
                    .then(setEmpiricalDocuments)
                    .catch(err => console.error('Error fetching docs:', err))
            }
        }
        fetchDocs()

        window.addEventListener('empirical_refresh', fetchDocs)
        return () => window.removeEventListener('empirical_refresh', fetchDocs)
    }, [projectId, setEmpiricalDocuments])

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        setError(null)
        try {
            await empiricalApi.upload(projectId, file)
            const updatedList = await empiricalApi.list(projectId)
            setEmpiricalDocuments(updatedList)
        } catch (err: any) {
            setError(err.message || 'Falha no upload')
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="flex flex-col h-full bg-slate-900/50 p-4">
            <header className="mb-6">
                <h3 className="text-white font-semibold text-lg mb-1">Mesa-Redonda</h3>
                <p className="text-slate-400 text-xs">Gestão de Evidências Empíricas (PDF/CSV)</p>
            </header>

            <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2 custom-scrollbar">
                {empiricalDocuments.length === 0 ? (
                    <div className="border-2 border-dashed border-white/5 rounded-2xl p-8 text-center">
                        <p className="text-slate-500 text-sm">Nenhum documento carregado.</p>
                    </div>
                ) : (
                    empiricalDocuments.map((doc, i) => (
                        <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3 group hover:border-indigo-500/50 transition cursor-default">
                            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition">
                                <span className="text-[10px] font-bold uppercase">{doc.split('.').pop()}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-white text-xs font-medium truncate">{doc}</p>
                                <p className="text-slate-500 text-[10px]">Indexado no Qdrant</p>
                            </div>
                        </div>
                    ))
                )}
            </div>

            <div className="space-y-3">
                {error && <p className="text-red-400 text-xs px-1">{error}</p>}

                <label className={`
                    w-full flex flex-col items-center justify-center px-4 py-6 
                    border-2 border-dashed rounded-2xl cursor-pointer transition
                    ${uploading ? 'border-slate-700 bg-slate-800/50 cursor-not-allowed' : 'border-indigo-500/20 bg-indigo-500/5 hover:bg-indigo-500/10 hover:border-indigo-500/40'}
                `}>
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <svg className="w-8 h-8 mb-3 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="mb-2 text-sm text-slate-300">
                            <span className="font-semibold">{uploading ? 'A enviar...' : 'Clique para carregar'}</span>
                        </p>
                        <p className="text-xs text-slate-500">PDF ou CSV (Max 10MB)</p>
                    </div>
                    <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.csv"
                        onChange={handleFileUpload}
                        disabled={uploading}
                    />
                </label>
            </div>
        </div>
    )
}
