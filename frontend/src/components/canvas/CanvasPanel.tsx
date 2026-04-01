'use client'
import { useState } from 'react'
import { useProjectStore, CanvasState } from '@/store/project'
import { projectsApi } from '@/lib/api'
import EvidenceManager from '@/components/project/EvidenceManager'
import KnowledgeGraph from '@/components/whiteboard/KnowledgeGraph'
import { getAlmaMetadata } from '@/lib/colors'


const FIELD_LABELS: Record<string, string> = {
    tema: 'Tema',
    problema: 'Problema de Investigação',
    justificativa: 'Justificativa',
    objetivos: 'Objectivos',
    metodologia: 'Metodologia',
}

interface Props {
    projectId: string
}

export default function CanvasPanel({ projectId }: Props) {
    const { canvas, updateCanvas, empiricalDocuments, activeAlmas } = useProjectStore()
    const [activeTab, setActiveTab] = useState<'canvas' | 'evidence' | 'whiteboard'>('canvas')
    const [editingField, setEditingField] = useState<string | null>(null)

    const [editValue, setEditValue] = useState('')
    const [saving, setSaving] = useState(false)

    function startEdit(field: string, currentValue: string) {
        if (canvas[field as keyof CanvasState] && typeof canvas[field as keyof CanvasState] === 'object') {
            const obj = canvas[field as keyof CanvasState] as Record<string, unknown>
            if ('is_locked' in obj && obj.is_locked) return
        }
        setEditingField(field)
        setEditValue(currentValue)
    }

    async function saveEdit() {
        if (!editingField) return
        setSaving(true)
        try {
            const updated = await projectsApi.patchCanvas(projectId, editingField, editValue) as CanvasState
            updateCanvas(updated)
            setEditingField(null)
        } catch (e) {
            console.error('Canvas save error', e)
        } finally {
            setSaving(false)
        }
    }

    function exportCanvas() {
        const blob = new Blob([JSON.stringify(canvas, null, 2)], { type: 'application/json' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `canvas-${projectId}.json`
        a.click()
    }

    function getFieldDisplayValue(key: string): { value: string; locked: boolean; auto: boolean } {
        const raw = canvas[key as keyof CanvasState]
        if (!raw) return { value: '', locked: false, auto: false }

        if (key === 'tema' || key === 'problema' || key === 'justificativa') {
            const f = raw as { content: string; is_locked: boolean }
            return { value: f.content, locked: f.is_locked, auto: f.content !== '' }
        }
        if (key === 'objetivos') {
            const f = raw as { geral: string; especificos: string[] }
            const parts = [f.geral, ...(f.especificos || [])].filter(Boolean)
            return { value: parts.join('\n'), locked: false, auto: parts.length > 0 }
        }
        if (key === 'metodologia') {
            const f = raw as { tipo: string; instrumentos: string[] }
            const val = [f.tipo, ...(f.instrumentos || [])].filter(Boolean).join(', ')
            return { value: val, locked: false, auto: val !== '' }
        }
        return { value: String(raw), locked: false, auto: false }
    }

    return (
        <div className="h-full flex flex-col bg-slate-900/80">
            <header className="px-5 py-3 border-b border-white/10 flex items-center justify-between gap-4">
                <nav className="flex gap-4">
                    <button
                        onClick={() => setActiveTab('canvas')}
                        className={`text-xs font-bold uppercase tracking-widest transition ${activeTab === 'canvas' ? 'text-white border-b-2 border-indigo-500 pb-1' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        Draft
                    </button>
                    <button
                        onClick={() => setActiveTab('evidence')}
                        className={`text-xs font-bold uppercase tracking-widest transition ${activeTab === 'evidence' ? 'text-white border-b-2 border-indigo-500 pb-1' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        Mesa-Redonda
                    </button>
                    <button
                        onClick={() => setActiveTab('whiteboard')}
                        className={`text-xs font-bold uppercase tracking-widest transition ${activeTab === 'whiteboard' ? 'text-white border-b-2 border-indigo-500 pb-1' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        Whiteboard
                    </button>
                </nav>
                {activeTab === 'canvas' && (
                    <button
                        id="export-canvas-button"
                        onClick={exportCanvas}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 transition"
                    >
                        Exportar JSON
                    </button>
                )}
            </header>

            <div className="flex-1 overflow-hidden">
                {activeTab === 'canvas' ? (
                    <div className="h-full overflow-y-auto px-4 py-4 space-y-3 custom-scrollbar">
                        {Object.keys(FIELD_LABELS).map((key) => {
                            const { value, locked, auto } = getFieldDisplayValue(key)
                            const isEditing = editingField === key

                            return (
                                <div
                                    key={key}
                                    className={`rounded-xl border p-3 transition ${auto ? 'border-indigo-500/40 bg-indigo-900/10' : 'border-white/10 bg-white/5'
                                        }`}
                                >
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
                                            {FIELD_LABELS[key]}
                                        </span>
                                        {auto && (
                                            <span className="text-[9px] bg-indigo-600/30 text-indigo-400 px-1.5 py-0.5 rounded-full">Auto</span>
                                        )}
                                        {locked && <span className="text-[10px] text-slate-500">🔒</span>}
                                    </div>

                                    {isEditing ? (
                                        <div>
                                            <textarea
                                                id={`canvas-edit-${key}`}
                                                rows={3}
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                className="w-full bg-white/10 border border-indigo-400/50 rounded-lg px-3 py-2 text-white text-xs resize-none focus:outline-none"
                                                autoFocus
                                            />
                                            <div className="flex gap-2 mt-1.5">
                                                <button onClick={saveEdit} disabled={saving}
                                                    className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded-lg transition">
                                                    {saving ? '...' : 'Guardar'}
                                                </button>
                                                <button onClick={() => setEditingField(null)}
                                                    className="text-xs text-slate-400 hover:text-white transition">
                                                    Cancelar
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <p
                                            onClick={() => !locked && startEdit(key, value)}
                                            className={`text-sm text-slate-300 leading-relaxed min-h-[1.5rem] ${!locked ? 'cursor-pointer hover:text-white transition' : ''
                                                } ${!value ? 'italic text-slate-600 text-xs' : ''}`}
                                        >
                                            {value || 'Ainda por definir...'}
                                        </p>
                                    )}
                                </div>
                            )
                        })}

                        {/* Bloco de Referências e Documentos */}
                        <div className={`rounded-xl border p-3 transition ${empiricalDocuments.length > 0 ? 'border-indigo-500/40 bg-indigo-900/10' : 'border-white/10 bg-white/5'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
                                    Referências e Empiria
                                </span>
                                {empiricalDocuments.length > 0 && (
                                    <span className="text-[9px] bg-indigo-600/30 text-indigo-400 px-1.5 py-0.5 rounded-full">
                                        {empiricalDocuments.length}
                                    </span>
                                )}
                            </div>

                            <div className="space-y-1.5">
                                {empiricalDocuments.length === 0 ? (
                                    <p className="text-xs text-slate-600 italic">Sem documentos. Use o botão + no chat para adicionar.</p>
                                ) : (
                                    empiricalDocuments.map((doc: string, idx: number) => (
                                        <div key={idx} className="flex items-center gap-2 text-xs text-slate-300">
                                            <span className="text-indigo-400 shrink-0">📄</span>
                                            <span className="truncate">{doc}</span>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Almas Ativas */}
                        <div className={`rounded-xl border p-3 mt-4 transition ${activeAlmas.length > 0 ? 'border-indigo-500/40 bg-indigo-900/10' : 'border-white/10 bg-white/5'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
                                    Almas Ativas (Conselho)
                                </span>
                                {activeAlmas.length > 0 && (
                                    <span className="text-[9px] bg-indigo-600/30 text-indigo-400 px-1.5 py-0.5 rounded-full">
                                        {activeAlmas.length}
                                    </span>
                                )}
                            </div>

                            <div className="space-y-2">
                                {activeAlmas.length === 0 ? (
                                    <p className="text-xs text-slate-600 italic">Nenhuma alma selecionada no projeto.</p>
                                ) : (
                                    activeAlmas.map((alma, idx) => {
                                        const metadata = getAlmaMetadata(alma.id, activeAlmas)
                                        const emoji = metadata?.emoji || '👤'
                                        const isTheoretical = String(alma.alma_type).toLowerCase().includes('theor');
                                        
                                        return (
                                            <div key={alma.id} className="flex items-center gap-2.5 group/alma">
                                                <span className={`shrink-0 text-base filter grayscale-[0.2] group-hover/alma:grayscale-0 transition-all ${metadata?.text || 'text-slate-400'}`}>
                                                    {emoji}
                                                </span>
                                                <div className="flex flex-col min-w-0">
                                                    <span className={`text-white text-[13px] font-medium truncate group-hover/alma:text-indigo-300 transition-colors`}>
                                                        {alma.name}
                                                    </span>
                                                    <span className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">
                                                        {isTheoretical ? 'Perspectiva Teórica' : 'Rigor Metodológico'}
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    })
                                )}
                            </div>
                        </div>
                    </div>
                ) : activeTab === 'evidence' ? (
                    <EvidenceManager projectId={projectId} />
                ) : (
                    <div className="h-full w-full">
                        <KnowledgeGraph />
                    </div>
                )}
            </div>
        </div>
    )
}
