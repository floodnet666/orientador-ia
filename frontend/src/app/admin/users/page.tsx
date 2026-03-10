"use client"
import { useEffect, useState } from "react"
import { adminApi } from "@/lib/api"

export default function AdminUsers() {
    const [users, setUsers] = useState<any[]>([])
    const [showNew, setShowNew] = useState(false)
    const [form, setForm] = useState({ email: "", full_name: "", password: "", academic_level: "MASTERS" })
    const [resetId, setResetId] = useState<string | null>(null)
    const [newPass, setNewPass] = useState("")

    const load = () => adminApi.getUsers().then(setUsers)
    useEffect(() => { load() }, [])

    const handleCreate = async () => {
        try {
            await adminApi.createUser(form)
            setShowNew(false)
            load()
        } catch (e: any) { alert(e.message) }
    }
    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure?")) return
        try {
            await adminApi.deleteUser(id)
            load()
        } catch (e: any) { alert(e.message) }
    }
    const handleReset = async (id: string) => {
        try {
            await adminApi.resetPassword(id, { new_password: newPass })
            setResetId(null)
            setNewPass("")
            alert("Password updated")
        } catch (e: any) { alert(e.message) }
    }
    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">Users Management</h1>
                <button onClick={() => setShowNew(true)} className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded text-white font-semibold shadow-md">
                    + Add User
                </button>
            </div>

            {showNew && (
                <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl space-y-4">
                    <h3 className="text-xl font-bold">New User</h3>
                    <input className="w-full bg-gray-900 border border-gray-700 rounded p-3 text-white" placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                    <input className="w-full bg-gray-900 border border-gray-700 rounded p-3 text-white" placeholder="Full Name" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
                    <input className="w-full bg-gray-900 border border-gray-700 rounded p-3 text-white" placeholder="Password" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
                    <select className="w-full bg-gray-900 border border-gray-700 rounded p-3 text-white" value={form.academic_level} onChange={e => setForm({ ...form, academic_level: e.target.value })}>
                        <option value="HIGHSCHOOL">High School</option>
                        <option value="BACHELORS">Bachelors</option>
                        <option value="MASTERS">Masters</option>
                        <option value="PHD">PhD</option>
                    </select>
                    <div className="flex space-x-3">
                        <button onClick={handleCreate} className="bg-green-600 hover:bg-green-500 px-6 py-2 rounded text-white font-bold">Save</button>
                        <button onClick={() => setShowNew(false)} className="bg-gray-600 hover:bg-gray-500 px-6 py-2 rounded text-white">Cancel</button>
                    </div>
                </div>
            )}

            <div className="bg-gray-800 rounded-lg shadow-xl overflow-hidden border border-gray-700">
                <table className="w-full text-left text-gray-300">
                    <thead className="bg-gray-900/50 border-b border-gray-700">
                        <tr>
                            <th className="px-6 py-3">User</th>
                            <th className="px-6 py-3">Academic Level</th>
                            <th className="px-6 py-3">Created</th>
                            <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {users.map(u => (
                            <tr key={u.id} className="hover:bg-gray-750/50">
                                <td className="px-6 py-4">
                                    <div className="font-bold text-white">{u.full_name} {u.is_admin && <span className="bg-purple-900 text-purple-300 px-2 py-0.5 rounded text-xs ml-2">ADMIN</span>}</div>
                                    <div className="text-sm text-gray-500">{u.email}</div>
                                </td>
                                <td className="px-6 py-4">{u.academic_level}</td>
                                <td className="px-6 py-4">{new Date(u.created_at).toLocaleDateString()}</td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button onClick={() => setResetId(u.id)} className="text-yellow-500 hover:text-yellow-400 text-sm px-2">Reset Pwd</button>
                                    <button onClick={() => handleDelete(u.id)} className="text-red-500 hover:text-red-400 text-sm px-2">Delete</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {resetId && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
                    <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full shadow-2xl border border-gray-700 animate-in zoom-in-95 duration-200">
                        <h3 className="text-xl font-bold mb-4">Reset Password</h3>
                        <input className="w-full bg-gray-900 border border-gray-700 rounded p-3 mb-4 text-white" placeholder="New Password" type="password" value={newPass} onChange={e => setNewPass(e.target.value)} />
                        <div className="flex space-x-3">
                            <button onClick={() => handleReset(resetId)} className="bg-yellow-600 hover:bg-yellow-500 flex-1 py-2 rounded font-bold text-black">Confirm</button>
                            <button onClick={() => setResetId(null)} className="bg-gray-600 hover:bg-gray-500 flex-1 py-2 rounded">Cancel</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
