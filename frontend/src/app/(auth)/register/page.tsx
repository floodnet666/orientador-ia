'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api'
import Link from 'next/link'

const ACADEMIC_LEVELS = [
    { value: 'HIGHSCHOOL', label: 'Ensino Secundário' },
    { value: 'BACHELORS', label: 'Licenciatura' },
    { value: 'MASTERS', label: 'Mestrado' },
    { value: 'PHD', label: 'Doutoramento' },
]

export default function RegisterPage() {
    const router = useRouter()
    const [form, setForm] = useState({
        full_name: '',
        email: '',
        password: '',
        academic_level: 'MASTERS',
    })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const update = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        setLoading(true)
        setError('')
        try {
            const { access_token } = await authApi.register(form)
            localStorage.setItem('token', access_token)
            router.push('/dashboard')
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Registration failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 flex items-center justify-center px-4">
            <div className="w-full max-w-md bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 shadow-2xl">
                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-bold text-white mb-2">Criar Conta</h1>
                    <p className="text-slate-400 text-sm">Orientador.IA — Registo de Investigador</p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {[
                        { id: 'full_name', label: 'Nome Completo', type: 'text', placeholder: 'João Silva' },
                        { id: 'email', label: 'Email', type: 'email', placeholder: 'seu@email.com' },
                        { id: 'password', label: 'Password', type: 'password', placeholder: '••••••••' },
                    ].map(({ id, label, type, placeholder }) => (
                        <div key={id}>
                            <label className="block text-sm text-slate-300 mb-1">{label}</label>
                            <input
                                id={id}
                                type={type}
                                value={form[id as keyof typeof form]}
                                onChange={(e) => update(id, e.target.value)}
                                required
                                placeholder={placeholder}
                                className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400 transition"
                            />
                        </div>
                    ))}
                    <div>
                        <label className="block text-sm text-slate-300 mb-1">Nível Académico</label>
                        <select
                            id="academic_level"
                            value={form.academic_level}
                            onChange={(e) => update('academic_level', e.target.value)}
                            className="w-full bg-slate-800 border border-white/20 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-400 transition"
                        >
                            {ACADEMIC_LEVELS.map((l) => (
                                <option key={l.value} value={l.value}>{l.label}</option>
                            ))}
                        </select>
                    </div>
                    {error && <p className="text-red-400 text-sm">{error}</p>}
                    <button
                        id="register-button"
                        type="submit"
                        disabled={loading}
                        className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold rounded-lg py-2.5 transition"
                    >
                        {loading ? 'A registar...' : 'Criar Conta'}
                    </button>
                </form>
                <p className="text-center text-slate-400 text-sm mt-6">
                    Já tem conta?{' '}
                    <Link href="/login" className="text-indigo-400 hover:text-indigo-300">
                        Entrar
                    </Link>
                </p>
            </div>
        </main>
    )
}
