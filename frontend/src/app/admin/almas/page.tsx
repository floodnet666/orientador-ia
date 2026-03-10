"use client"
import { useEffect, useState } from "react"
import { adminApi } from "@/lib/api"

export default function AdminAlmas() {
    const [almas, setAlmas] = useState<any[]>([])
    const [models, setModels] = useState<string[]>([])
    const [showNew, setShowNew] = useState(false)
    const [form, setForm] = useState({ name: "", description: "", resource_type: "ALMA", alma_type: "THEORETICAL", system_prompt: "", personality_descriptor: "", llm_model: "qwen3.5:4b" })
    const [updating, setUpdating] = useState<string | null>(null)
    const [statusMsg, setStatusMsg] = useState<{ id: string, type: 'success' | 'error', text: string } | null>(null)
    const [promptMode, setPromptMode] = useState<any>(null)

    const load = () => {
        adminApi.getAlmas().then(setAlmas)
        adminApi.getOllamaModels().then(setModels)
    }
    useEffect(() => { load() }, [])

    const loadHistory = (almaId: string) => {
        adminApi.getPromptHistory(almaId).then(history => {
            setPromptMode((prev: any) => ({ ...prev, history }))
        })
    }

    const openPromptMode = (alma: any) => {
        setPromptMode({ alma, newPrompt: alma.system_prompt, reason: "", history: [] })
        loadHistory(alma.id)
    }

    const handleCreate = async () => {
        try {
            await adminApi.createAlma(form)
            setShowNew(false)
            load()
        } catch (e: any) { alert(e.message) }
    }

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this Alma?")) return
        try {
            await adminApi.deleteAlma(id)
            load()
        } catch (e: any) { alert(e.message) }
    }

    const handleUpdatePrompt = async () => {
        try {
            await adminApi.updatePrompt(promptMode.alma.id, { new_prompt: promptMode.newPrompt, reason: promptMode.reason })
            alert("System Prompt updated! Version saved to history.")
            setPromptMode(null)
            load()
        } catch (e: any) { alert(e.message) }
    }

    const handleRollback = async (historyId: string) => {
        if (!confirm("Are you sure you want to rollback to this previous prompt?")) return
        try {
            await adminApi.rollbackPrompt(promptMode.alma.id, historyId)
            alert("Prompt rolled back successfully.")
            setPromptMode(null)
            load()
        } catch (e: any) { alert(e.message) }
    }

    const updateLlmModel = async (almaId: string, modelStr: string) => {
        setUpdating(almaId)
        try {
            await adminApi.updateAlma(almaId, { llm_model: modelStr })
            setStatusMsg({ id: almaId, type: 'success', text: 'Model saved!' })
            load()
            setTimeout(() => setStatusMsg(null), 3000)
        } catch (e: any) {
            setStatusMsg({ id: almaId, type: 'error', text: e.message })
        } finally {
            setUpdating(null)
        }
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">Almas Management</h1>
                <button onClick={() => setShowNew(true)} className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded text-white font-semibold shadow-md">
                    + Add Alma
                </button>
            </div>

            {showNew && (
                <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl space-y-4 grid grid-cols-2 gap-4">
                    <div className="col-span-2"><h3 className="text-xl font-bold border-b border-gray-700 pb-2">New Alma Definition</h3></div>
                    <input className="w-full bg-gray-900 border border-gray-700 rounded p-3" placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                    <select className="w-full bg-gray-900 border border-gray-700 rounded p-3" value={form.llm_model} onChange={e => setForm({ ...form, llm_model: e.target.value })}>
                        <option value="" disabled>Select Model</option>
                        {models.map(m => <option key={m} value={m}>{m}</option>)}
                        {!models.includes(form.llm_model) && <option value={form.llm_model}>{form.llm_model} (Manual)</option>}
                    </select>
                    <textarea className="col-span-2 w-full bg-gray-900 border border-gray-700 rounded p-3 h-24" placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                    <select className="w-full bg-gray-900 border border-gray-700 rounded p-3" value={form.resource_type} onChange={e => setForm({ ...form, resource_type: e.target.value })}>
                        <option value="ALMA">Alma</option>
                        <option value="SKILL">Skill</option>
                        <option value="TOOL">Tool</option>
                    </select>
                    <select className="w-full bg-gray-900 border border-gray-700 rounded p-3" value={form.alma_type} onChange={e => setForm({ ...form, alma_type: e.target.value })}>
                        <option value="THEORETICAL">Theoretical</option>
                        <option value="METHODOLOGICAL">Methodological</option>
                    </select>
                    <textarea className="col-span-2 w-full bg-gray-900 border border-gray-700 rounded p-3 h-32" placeholder="System Prompt" value={form.system_prompt} onChange={e => setForm({ ...form, system_prompt: e.target.value })} />
                    <textarea className="col-span-2 w-full bg-gray-900 border border-gray-700 rounded p-3 h-24" placeholder="Personality Descriptor" value={form.personality_descriptor} onChange={e => setForm({ ...form, personality_descriptor: e.target.value })} />
                    <div className="col-span-2 flex justify-end space-x-3 pt-2">
                        <button onClick={() => setShowNew(false)} className="bg-gray-600 hover:bg-gray-500 px-6 py-2 rounded">Cancel</button>
                        <button onClick={handleCreate} className="bg-green-600 hover:bg-green-500 px-6 py-2 rounded font-bold">Register Alma</button>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {almas.map(a => (
                    <div key={a.id} className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-lg flex flex-col justify-between hover:border-gray-500 transition-colors">
                        <div>
                            <div className="flex justify-between items-start mb-2">
                                <h3 className="font-bold text-xl text-white">{a.name}</h3>
                                <div className="space-x-1 flex flex-col items-end gap-1">
                                    <span className="text-xs px-2 py-1 bg-gray-700 rounded">{a.alma_type}</span>
                                    {a.llm_model && <span className="text-xs px-2 py-1 bg-blue-900/50 text-blue-300 rounded border border-blue-800 shrink-0">{a.llm_model}</span>}
                                </div>
                            </div>
                            <p className="text-sm text-gray-400 mb-4 line-clamp-3 leading-relaxed">{a.description}</p>

                            <div className="mb-4">
                                <label className="text-xs text-gray-500 uppercase tracking-wider block mb-1">Set LLM Model</label>
                                <div className="relative">
                                    <select
                                        className={`w-full bg-gray-900 text-sm border border-gray-700 rounded px-3 py-2 text-white transition-opacity ${updating === a.id ? 'opacity-50' : 'opacity-100'}`}
                                        value={a.llm_model || ""}
                                        disabled={updating === a.id}
                                        onChange={(e) => updateLlmModel(a.id, e.target.value)}
                                    >
                                        <option value="" disabled>Select Model</option>
                                        {models.map(m => <option key={m} value={m}>{m}</option>)}
                                        {a.llm_model && !models.includes(a.llm_model) && <option value={a.llm_model}>{a.llm_model} (Manual)</option>}
                                    </select>

                                    {updating === a.id && (
                                        <div className="absolute right-8 top-2.5">
                                            <div className="animate-spin h-3 w-3 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                                        </div>
                                    )}

                                    {statusMsg && statusMsg.id === a.id && (
                                        <span className={`absolute -top-6 right-0 text-[10px] font-bold uppercase tracking-tighter ${statusMsg.type === 'success' ? 'text-green-400' : 'text-red-400'} animate-bounce`}>
                                            {statusMsg.text}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-700">
                            <button onClick={() => handleDelete(a.id)} className="text-red-500 hover:text-red-400 text-sm font-medium">Delete</button>
                            <button onClick={() => openPromptMode(a)} className="bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 border border-blue-800 px-4 py-1.5 rounded text-sm font-medium transition-colors">Edit Prompt / History</button>
                        </div>
                    </div>
                ))}
            </div>

            {promptMode && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
                    <div className="bg-gray-800 rounded-xl p-6 max-w-4xl w-full shadow-2xl border border-gray-700 max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center border-b border-gray-700 pb-4 mb-4">
                            <h3 className="text-2xl font-bold">Manage Prompt: {promptMode.alma.name}</h3>
                            <button onClick={() => setPromptMode(null)} className="text-gray-400 hover:text-white text-3xl leading-none">&times;</button>
                        </div>

                        <div className="grid grid-cols-2 gap-8">
                            <div className="space-y-4">
                                <div>
                                    <label className="text-sm text-gray-400 font-bold block mb-2">Edit Current System Prompt</label>
                                    <textarea
                                        className="w-full bg-gray-900 border border-gray-700 rounded p-4 h-64 text-gray-300 font-mono text-sm leading-relaxed"
                                        value={promptMode.newPrompt}
                                        onChange={e => setPromptMode({ ...promptMode, newPrompt: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="text-sm text-gray-400 font-bold block mb-2">Reason for modification (for history)</label>
                                    <input
                                        className="w-full bg-gray-900 border border-gray-700 rounded p-3 text-white"
                                        placeholder="e.g. 'Improved response instructions for debate mode'"
                                        value={promptMode.reason}
                                        onChange={e => setPromptMode({ ...promptMode, reason: e.target.value })}
                                    />
                                </div>
                                <button onClick={handleUpdatePrompt} className="w-full bg-blue-600 hover:bg-blue-500 py-3 rounded font-bold shadow-lg">Save New Prompt</button>
                            </div>

                            <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700 flex flex-col h-full">
                                <h4 className="text-lg font-bold mb-4 flex items-center gap-2"><span className="text-xl">🕰️</span> Version History</h4>
                                <div className="space-y-4 overflow-y-auto flex-1 pr-2">
                                    {promptMode.history.length === 0 && <p className="text-gray-500 italic text-center py-8">No history recorded yet.</p>}
                                    {promptMode.history.map((h: any) => (
                                        <div key={h.id} className="bg-gray-800 p-4 rounded border border-gray-700 shadow-sm relative group overflow-hidden">
                                            <div className="text-xs text-gray-500 mb-2">{new Date(h.changed_at).toLocaleString()}</div>
                                            <div className="text-sm text-gray-300 font-medium mb-3">"{h.reason || "No reason provided"}"</div>
                                            <div className="text-xs text-gray-500 font-mono bg-gray-900 p-2 rounded line-clamp-3 border border-gray-700/50">{h.previous_prompt}</div>
                                            <div className="mt-3 flex justify-end">
                                                <button onClick={() => handleRollback(h.id)} className="text-xs bg-yellow-600/20 text-yellow-500 hover:bg-yellow-600 hover:text-white border border-yellow-800 px-3 py-1 rounded transition-colors font-medium">Rollback to this</button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
