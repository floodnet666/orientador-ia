'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { projectsApi } from '@/lib/api'
import Link from 'next/link'
import GenesisModal from '@/components/dashboard/GenesisModal'

interface Project {
    id: string
    title: string
    domain_area: string
    academic_level: string
    status: string
    created_at: string
}

const STATUS_COLORS: Record<string, string> = {
    DRAFT: 'bg-slate-600',
    REVIEW: 'bg-yellow-600',
    ANALYSIS: 'bg-blue-600',
    COMPLETE: 'bg-green-600',
}

export default function DashboardPage() {
    const router = useRouter()
    const [projects, setProjects] = useState<Project[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [showNew, setShowNew] = useState(false)
    const [showGenesis, setShowGenesis] = useState(false)
    const [newForm, setNewForm] = useState({ title: '', domain_area: '', academic_level: 'MASTERS' })
    const [creating, setCreating] = useState(false)

    useEffect(() => {
        if (!localStorage.getItem('token')) {
            router.push('/login')
            return
        }
        projectsApi.list().then((ps) => setProjects(ps as Project[])).catch(() => {
            localStorage.removeItem('token')
            router.push('/login')
        }).finally(() => setLoading(false))
    }, [router])

    async function createProject() {
        setCreating(true)
        try {
            const project = await projectsApi.create(newForm) as Project
            router.push(`/project/${project.id}/match`)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Error creating project')
        } finally {
            setCreating(false)
        }
    }

    if (loading) return (
        <main className="min-h-screen bg-slate-900 flex items-center justify-center">
            <div className="text-white">A carregar...</div>
        </main>
    )

    return (
        <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 px-4 py-8">
            <div className="max-w-5xl mx-auto">
                <header className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white">Orientador.IA</h1>
                        <p className="text-slate-400 text-sm mt-1">Os seus projectos de investigação</p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={() => setShowGenesis(true)}
                            className="text-indigo-400 border border-indigo-500/30 hover:bg-indigo-500/10 px-4 py-2 rounded-lg text-sm transition"
                        >
                            ✨ Génesis
                        </button>
                        <button
                            id="logout-button"
                            onClick={() => { localStorage.removeItem('token'); router.push('/login') }}
                            className="text-slate-400 hover:text-white text-sm transition px-2"
                        >
                            Sair
                        </button>
                        <button
                            id="new-project-button"
                            onClick={() => setShowNew(true)}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-lg text-sm transition"
                        >
                            + Novo Projeto
                        </button>
                    </div>
                </header>

                <GenesisModal
                    isOpen={showGenesis}
                    onClose={() => setShowGenesis(false)}
                    onCreated={() => {
                        // In a real app we might toast success here
                    }}
                />

                {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

                {showNew && (
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-8">
                        <h2 className="text-white font-semibold mb-4">Novo Projeto de Investigação</h2>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                            <div>
                                <label className="block text-sm text-slate-300 mb-1">Título</label>
                                <input value={newForm.title} onChange={(e) => setNewForm(f => ({ ...f, title: e.target.value }))}
                                    id="new-title" placeholder="Ex: Vigilância Digital" className="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-400" />
                            </div>
                            <div>
                                <label className="block text-sm text-slate-300 mb-1">Área Temática</label>
                                <input value={newForm.domain_area} onChange={(e) => setNewForm(f => ({ ...f, domain_area: e.target.value }))}
                                    id="new-area" placeholder="Ex: Sociologia Digital" className="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-400" />
                            </div>
                            <div>
                                <label className="block text-sm text-slate-300 mb-1">Nível Académico</label>
                                <select value={newForm.academic_level} onChange={(e) => setNewForm(f => ({ ...f, academic_level: e.target.value }))}
                                    className="w-full bg-slate-800 border border-white/20 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-400">
                                    <option value="HIGHSCHOOL">Secundário</option>
                                    <option value="BACHELORS">Licenciatura</option>
                                    <option value="MASTERS">Mestrado</option>
                                    <option value="PHD">Doutoramento</option>
                                </select>
                            </div>
                        </div>
                        <div className="flex gap-2 mt-4">
                            <button id="create-project-button" onClick={createProject} disabled={creating || !newForm.title || !newForm.domain_area}
                                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition">
                                {creating ? 'A criar...' : 'Criar e Selecionar Almas'}
                            </button>
                            <button onClick={() => setShowNew(false)} className="text-slate-400 hover:text-white text-sm px-4 py-2 transition">Cancelar</button>
                        </div>
                    </div>
                )}

                {projects.length === 0 ? (
                    <div className="text-center py-20">
                        <p className="text-slate-400 text-lg">Nenhum projeto ainda.</p>
                        <p className="text-slate-500 text-sm mt-2">Clique em &quot;Novo Projeto&quot; para começar.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {projects.map((p) => (
                            <Link key={p.id} href={`/project/${p.id}`}
                                className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl p-5 transition cursor-pointer group">
                                <div className="flex items-start justify-between mb-3">
                                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full text-white ${STATUS_COLORS[p.status] || 'bg-slate-600'}`}>
                                        {p.status}
                                    </span>
                                    <span className="text-xs text-slate-500">{p.academic_level}</span>
                                </div>
                                <h3 className="text-white font-semibold group-hover:text-indigo-300 transition">{p.title}</h3>
                                <p className="text-slate-400 text-sm mt-1">{p.domain_area}</p>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </main>
    )
}
