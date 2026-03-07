'use client'

interface AlmaRole {
    name: string
    rationale?: string
    angle?: string
}

interface Panel {
    PRIMARIA: AlmaRole
    COMPLEMENTAR: AlmaRole
    ANTAGONISTA: AlmaRole
    METODOLOGICA: AlmaRole
}

interface Props {
    panel: Panel
    activeRole: string | null  // which alma is currently "typing"
}

const ROLE_CONFIG = {
    PRIMARIA: {
        label: 'Primária',
        color: 'border-violet-500 bg-violet-500/10 text-violet-300',
        dot: 'bg-violet-400',
        badge: 'bg-violet-500/20 text-violet-300 border-violet-500/40',
        icon: '⬤',
    },
    COMPLEMENTAR: {
        label: 'Complementar',
        color: 'border-cyan-500 bg-cyan-500/10 text-cyan-300',
        dot: 'bg-cyan-400',
        badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
        icon: '⬤',
    },
    ANTAGONISTA: {
        label: 'Antagonista',
        color: 'border-rose-500 bg-rose-500/10 text-rose-300',
        dot: 'bg-rose-400',
        badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
        icon: '⬤',
    },
    METODOLOGICA: {
        label: 'Metodológica',
        color: 'border-amber-500 bg-amber-500/10 text-amber-300',
        dot: 'bg-amber-400',
        badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
        icon: '⬤',
    },
}

export default function DebatePanel({ panel, activeRole }: Props) {
    return (
        <div className="px-4 py-3 border-b border-white/10 bg-slate-900/60 backdrop-blur-sm">
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2 font-semibold">
                Painel de Debate Activo
            </p>
            <div className="grid grid-cols-2 gap-2">
                {(Object.entries(panel) as [keyof typeof ROLE_CONFIG, AlmaRole][]).map(([role, alma]) => {
                    const cfg = ROLE_CONFIG[role]
                    const isActive = activeRole === role
                    return (
                        <div
                            key={role}
                            className={`rounded-lg border px-3 py-2 transition-all duration-300 ${cfg.color} ${isActive ? 'ring-2 ring-white/30 scale-[1.01]' : 'opacity-80'
                                }`}
                        >
                            <div className="flex items-center gap-1.5 mb-0.5">
                                <span className={`text-xs font-bold px-1.5 py-0.5 rounded border ${cfg.badge}`}>
                                    {cfg.label}
                                </span>
                                {isActive && (
                                    <span className="flex gap-0.5 ml-auto">
                                        <span className={`w-1 h-1 ${cfg.dot} rounded-full animate-bounce`} style={{ animationDelay: '0ms' }} />
                                        <span className={`w-1 h-1 ${cfg.dot} rounded-full animate-bounce`} style={{ animationDelay: '150ms' }} />
                                        <span className={`w-1 h-1 ${cfg.dot} rounded-full animate-bounce`} style={{ animationDelay: '300ms' }} />
                                    </span>
                                )}
                            </div>
                            <p className="text-xs font-semibold truncate">{alma.name}</p>
                            {(alma.rationale || alma.angle) && (
                                <p className="text-xs opacity-60 truncate mt-0.5">
                                    {alma.rationale || alma.angle}
                                </p>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
