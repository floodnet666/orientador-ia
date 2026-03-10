"use client"
import { useEffect, useState } from "react"
import { adminApi } from "@/lib/api"

export default function AdminDashboard() {
    const [metrics, setMetrics] = useState<any>(null)
    const [error, setError] = useState("")
    const [loading, setLoading] = useState(true)

    const loadMetrics = () => {
        setLoading(true)
        setError("")
        adminApi.getMetrics()
            .then(setMetrics)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false))
    }

    useEffect(() => {
        loadMetrics()
    }, [])

    if (error) return (
        <div className="p-6 bg-red-950/30 border border-red-900/50 rounded-xl space-y-4">
            <div className="text-red-400 font-bold text-lg flex items-center gap-2">
                <span>⚠️</span> Error loading metrics: {error}
            </div>
            <button
                onClick={loadMetrics}
                className="bg-red-800 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors font-semibold shadow-lg"
            >
                Retry Connection
            </button>
        </div>
    )
    if (loading && !metrics) return (
        <div className="flex items-center justify-center p-24">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
        </div>
    )

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight">Observability</h1>
                    <p className="text-gray-400 mt-2">Track real-time system metrics, bottlenecks, and errors.</p>
                </div>
                <button
                    onClick={loadMetrics}
                    disabled={loading}
                    className="bg-gray-800 hover:bg-gray-700 disabled:opacity-50 border border-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 transition-all active:scale-95 shadow-lg"
                >
                    <span className={`${loading ? 'animate-spin' : ''}`}>🔄</span>
                    {loading ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-8 rounded-2xl border border-gray-700 shadow-xl flex flex-col items-center justify-center">
                    <span className="text-sm text-gray-400 font-semibold uppercase tracking-wider">Avg Response Time</span>
                    <span className="text-5xl font-mono mt-4 text-blue-400 font-bold drop-shadow-md">{Math.round(metrics.average_duration_ms)} <span className="text-2xl text-blue-600">ms</span></span>
                </div>
                <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-8 rounded-2xl border border-gray-700 shadow-xl flex flex-col items-center justify-center relative overflow-hidden">
                    {metrics.slow_queries_count > 0 && (
                        <div className="absolute top-0 right-0 w-16 h-16 pointer-events-none">
                            <div className="absolute transform rotate-45 bg-red-500 text-center text-white font-semibold py-1 right-[-35px] top-[32px] w-[170px] text-xs">WARNING</div>
                        </div>
                    )}
                    <span className="text-sm text-gray-400 font-semibold uppercase tracking-wider">Slow Responses (&gt;40s)</span>
                    <span className={`text-5xl font-mono mt-4 font-bold drop-shadow-md ${metrics.slow_queries_count > 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {metrics.slow_queries_count}
                    </span>
                    <p className="text-xs text-gray-500 mt-2">LLM endpoints exceeding 40000ms</p>
                </div>
            </div>

            <div className={`bg-gray-800/80 backdrop-blur-sm rounded-2xl border border-gray-700 overflow-hidden shadow-2xl transition-opacity duration-300 ${loading ? 'opacity-50' : 'opacity-100'}`}>
                <div className="px-6 py-5 border-b border-gray-700 font-bold text-lg flex justify-between items-center bg-gray-900">
                    Recent Request Log
                    <span className="text-xs font-normal text-gray-400 px-3 py-1 bg-gray-800 rounded-full border border-gray-700">Last 100 entries</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-gray-300">
                        <thead className="bg-gray-900/50 text-xs uppercase text-gray-500 border-b border-gray-700/50">
                            <tr>
                                <th className="px-6 py-4 font-semibold tracking-wider">Timestamp</th>
                                <th className="px-6 py-4 font-semibold tracking-wider">Endpoint</th>
                                <th className="px-6 py-4 font-semibold tracking-wider">Status</th>
                                <th className="px-6 py-4 font-semibold tracking-wider text-right">Duration (ms)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/50">
                            {metrics.recent_metrics.map((m: any) => {
                                const isSlow = m.duration_ms > 40000;
                                const isError = m.status_code >= 400;
                                return (
                                    <tr key={m.id} className="hover:bg-gray-750/50 transition-colors group">
                                        <td className="px-6 py-3 whitespace-nowrap text-gray-400 group-hover:text-gray-300 transition-colors">{new Date(m.created_at).toLocaleString()}</td>
                                        <td className="px-6 py-3 break-all font-mono text-xs text-blue-200/70">{m.endpoint}</td>
                                        <td className="px-6 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${isError ? 'bg-red-900/50 text-red-300 border border-red-800' : 'bg-green-900/50 text-green-300 border border-green-800'}`}>
                                                {m.status_code}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3 whitespace-nowrap text-right">
                                            <span className={`font-mono px-2 py-1 rounded-md text-sm ${isSlow ? 'bg-red-900/40 text-red-400 font-bold animate-pulse' : 'text-gray-300'}`}>
                                                {m.duration_ms}
                                            </span>
                                        </td>
                                    </tr>
                                )
                            })}
                            {metrics.recent_metrics.length === 0 && (
                                <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500 italic">No telemetry data available yet</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
