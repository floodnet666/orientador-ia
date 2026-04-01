'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { projectsApi } from '@/lib/api'
import Link from 'next/link'
import GenesisModal from '@/components/dashboard/GenesisModal'
import { useHelp } from '@/store/HelpContext'
import HelpTooltip from '@/components/shared/HelpTooltip'

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
    const { toggleHelpMode, isHelpModeActive, hasSeenOnboarding, completeOnboarding } = useHelp()
    const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
    const [deleting, setDeleting] = useState(false)

    useEffect(() => {
        if (!loading && !hasSeenOnboarding && projects.length === 0) {
            // Se o utilizador não tem projetos e nunca viu o onboarding, ativamos a ajuda
            if (!isHelpModeActive) toggleHelpMode()
        }
    }, [loading, hasSeenOnboarding, projects.length])

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

    async function deleteProject(id: string) {
        setDeleting(true)
        try {
            await projectsApi.delete(id)
            setProjects((prev) => prev.filter((p) => p.id !== id))
            setProjectToDelete(null)
        } catch (e: unknown) {
            console.error('[ERRO] Falha ao deletar projeto:', e)
            alert(e instanceof Error ? e.message : 'Erro ao eliminar projeto')
        } finally {
            setDeleting(false)
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
                            onClick={toggleHelpMode}
                            className={`p-2 rounded-lg transition-colors ${isHelpModeActive ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white bg-white/5'}`}
                            title="Modo Ajuda"
                        >
                            ⁉️
                        </button>
                        <HelpTooltip content="O Génesis cria uma Alma personalizada do zero com base na sua necessidade.">
                            <button
                                onClick={() => setShowGenesis(true)}
                                className="text-indigo-400 border border-indigo-500/30 hover:bg-indigo-500/10 px-4 py-2 rounded-lg text-sm transition"
                            >
                                ✨ Génesis
                            </button>
                        </HelpTooltip>
                        <button
                            id="logout-button"
                            onClick={() => { localStorage.removeItem('token'); router.push('/login') }}
                            className="text-slate-400 hover:text-white text-sm transition px-2"
                        >
                            Sair
                        </button>
                        <HelpTooltip content="Inicie um novo projeto de investigação aqui.">
                            <button
                                id="new-project-button"
                                onClick={() => setShowNew(true)}
                                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-lg text-sm transition"
                            >
                                + Novo Projeto
                            </button>
                        </HelpTooltip>
                    </div>
                </header>

                {!hasSeenOnboarding && (
                    <div className="bg-indigo-600/20 border border-indigo-500/30 rounded-2xl p-6 mb-8 flex items-center justify-between">
                        <div>
                            <h2 className="text-white font-bold text-lg">Bem-vindo ao Orientador.IA! 🚀</h2>
                            <p className="text-indigo-200 text-sm">Ativamos o <b>Modo Ajuda (⁉️)</b> para guiá-lo no seu primeiro projeto. Passe o rato sobre os elementos com brilho azul para aprender.</p>
                        </div>
                        <button onClick={completeOnboarding} className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition">
                            Entendi!
                        </button>
                    </div>
                )}

                <GenesisModal
                    isOpen={showGenesis}
                    onClose={() => setShowGenesis(false)}
                    onCreated={(alma) => {
                        console.log('[DEBUG] Nova alma criada via Genesis:', alma.name)
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
                            <div key={p.id} className="relative group">
                                <Link
                                    href={`/project/${p.id}`}
                                    className="block bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl p-5 transition cursor-pointer"
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full text-white ${STATUS_COLORS[p.status] || 'bg-slate-600'}`}>
                                            {p.status}
                                        </span>
                                        <span className="text-xs text-slate-500 mr-8">{p.academic_level}</span>
                                    </div>
                                    <h3 className="text-white font-semibold group-hover:text-indigo-300 transition pr-10">{p.title}</h3>
                                    <p className="text-slate-400 text-sm mt-1">{p.domain_area}</p>
                                </Link>
                                <button
                                    onClick={(e) => {
                                        e.preventDefault()
                                        e.stopPropagation()
                                        console.log('[DEBUG] 🗑️ Iniciando processo de deleção para:', p.title)
                                        setProjectToDelete(p)
                                    }}
                                    className="absolute top-4 right-4 text-slate-400 hover:text-red-400 p-2 rounded-xl transition-all bg-white/10 hover:bg-red-500/20 z-50 border border-white/5"
                                    title="Eliminar Projeto"
                                >
                                    🗑️
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal de Confirmação de Deleção */}
            {projectToDelete && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
                    <div className="bg-slate-900 border border-white/10 rounded-2xl p-6 max-w-sm w-full shadow-2xl animate-in zoom-in-95 duration-200">
                        <h3 className="text-xl font-bold text-white mb-2">Eliminar Projeto?</h3>
                        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                            Tem a certeza que deseja eliminar o projeto <span className="text-indigo-400 font-semibold text-base block mt-1">&quot;{projectToDelete.title}&quot;</span>? Esta ação removerá todos os dados associados.
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setProjectToDelete(null)}
                                disabled={deleting}
                                className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-white text-sm font-medium transition disabled:opacity-50"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={() => deleteProject(projectToDelete.id)}
                                disabled={deleting}
                                className="flex-1 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-bold transition disabled:bg-red-600/50 flex items-center justify-center gap-2"
                            >
                                {deleting ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                        A eliminar...
                                    </>
                                ) : (
                                    'Sim, eliminar'
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </main>
    )
}
