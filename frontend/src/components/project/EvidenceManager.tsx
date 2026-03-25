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
    const [statuses, setStatuses] = useState<Record<string, string>>({})

    const fetchDocs = async () => {
        if (projectId) {
            try {
                const docs = await empiricalApi.list(projectId)
                setEmpiricalDocuments(docs)
                
                // Track non-completed statuses (not ideal for many docs, but fine for Mesa-Redonda)
                const newStatuses: Record<string, string> = {}
                for (const doc of docs) {
                    newStatuses[doc] = 'indexado'
                }
                setStatuses(prev => ({ ...prev, ...newStatuses }))
            } catch (err) {
                console.error('Error fetching docs:', err)
            }
        }
    }

    useEffect(() => {
        fetchDocs()
        window.addEventListener('empirical_refresh', fetchDocs)
        return () => window.removeEventListener('empirical_refresh', fetchDocs)
    }, [projectId, setEmpiricalDocuments])

    // Polling for processing documents
    useEffect(() => {
        const processingDocs = Object.entries(statuses).filter(([_, s]) => s === 'processing').map(([f]) => f)
        if (processingDocs.length === 0) return

        const interval = setInterval(async () => {
            for (const filename of processingDocs) {
                const { status } = await empiricalApi.getStatus(projectId, filename)
                if (status !== 'processing') {
                    setStatuses(prev => ({ ...prev, [filename]: status }))
                    if (status === 'completed') fetchDocs()
                }
            }
        }, 3000)

        return () => clearInterval(interval)
    }, [statuses, projectId])

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        setError(null)
        try {
            const res = await empiricalApi.upload(projectId, file)
            setStatuses(prev => ({ ...prev, [file.name]: 'processing' }))
            // Start polling status
            const checkStatus = async () => {
                const { status } = await empiricalApi.getStatus(projectId, file.name)
                setStatuses(prev => ({ ...prev, [file.name]: status }))
                if (status === 'completed') fetchDocs()
            }
            setTimeout(checkStatus, 2000)
        } catch (err: any) {
            setError(err.message || 'Falha no upload')
        } finally {
            setUploading(false)
        }
    }

    const handleDelete = async (filename: string) => {
        if (!confirm(`Remover "${filename}" da biblioteca?`)) return
        try {
            await empiricalApi.delete(projectId, filename)
            setEmpiricalDocuments(empiricalDocuments.filter(d => d !== filename))
        } catch (err: any) {
            setError(err.message || 'Erro ao apagar')
        }
    }

    return (
        <div className="flex flex-col h-full bg-slate-900/50 p-4">
            <header className="mb-6 flex justify-between items-start">
                <div>
                    <h3 className="text-white font-semibold text-lg mb-1">Mesa-Redonda</h3>
                    <p className="text-slate-400 text-xs font-mono lowercase opacity-70">RAG v2.2.0: SPLADE + Redis + BBox</p>
                </div>
                {uploading && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-indigo-500 border-t-transparent" />
                )}
            </header>

            <div className="flex-1 overflow-y-auto space-y-2 mb-4 pr-2 custom-scrollbar">
                {empiricalDocuments.length === 0 && !Object.values(statuses).includes('processing') ? (
                    <div className="border-2 border-dashed border-white/5 rounded-2xl p-8 text-center bg-white/[0.02]">
                        <p className="text-slate-500 text-sm">Nenhum documento carregado.</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {/* Listar documentos em processamento primeiro */}
                        {Object.entries(statuses)
                            .filter(([_, s]) => s === 'processing')
                            .map(([filename]) => (
                                <div key={`proc-${filename}`} className="bg-white/5 border border-indigo-500/30 rounded-xl p-3 flex items-center gap-3 animate-pulse">
                                    <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                                        <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-white text-xs font-medium truncate">{filename}</p>
                                        <p className="text-indigo-400 text-[9px] uppercase tracking-wider font-bold">Processando...</p>
                                    </div>
                                </div>
                            ))
                        }
                        
                        {empiricalDocuments.map((doc, i) => (
                            <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3 group hover:border-indigo-500/40 transition-all hover:bg-white/[0.08]">
                                <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-indigo-500/20 group-hover:text-indigo-400 transition">
                                    <span className="text-[10px] font-bold uppercase">{doc.split('.').pop()}</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-white text-xs font-medium truncate">{doc}</p>
                                    <p className="text-slate-500 text-[10px]">Pronto para consulta</p>
                                </div>
                                <button 
                                    onClick={() => handleDelete(doc)}
                                    className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/20 hover:text-red-400 text-slate-500 rounded-lg transition"
                                    title="Remover documento"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="space-y-3 pt-2 border-t border-white/5">
                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2 text-red-400 text-[10px] flex gap-2 items-center">
                        <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        {error}
                    </div>
                )}

                <label className={`
                    w-full flex flex-col items-center justify-center px-4 py-4 
                    border-2 border-dashed rounded-2xl cursor-pointer transition-all
                    ${uploading ? 'border-slate-700 bg-slate-800/50 cursor-wait' : 'border-indigo-500/20 bg-indigo-500/5 hover:bg-indigo-500/10 hover:border-indigo-500/40'}
                `}>
                    <div className="flex flex-col items-center justify-center py-2">
                        <svg className={`w-6 h-6 mb-2 ${uploading ? 'text-slate-500' : 'text-indigo-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-xs text-slate-300 font-medium">
                            {uploading ? 'A enviar ficheiro...' : 'Anexar evidência empírica'}
                        </p>
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
