export default function AdminLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex bg-gray-900 min-h-screen">
            <aside className="w-64 bg-gray-800 border-r border-gray-700 flex-shrink-0">
                <div className="p-4 border-b border-gray-700">
                    <h2 className="text-xl font-bold text-white tracking-widest uppercase text-center mt-2">Admin Panel</h2>
                </div>
                <nav className="p-4 space-y-2 text-gray-300 font-medium">
                    <a href="/admin" className="block p-3 rounded-lg hover:bg-gray-700 hover:text-white transition-colors">📊 Metrics</a>
                    <a href="/admin/users" className="block p-3 rounded-lg hover:bg-gray-700 hover:text-white transition-colors">👥 Users</a>
                    <a href="/admin/almas" className="block p-3 rounded-lg hover:bg-gray-700 hover:text-white transition-colors">🧠 Almas</a>
                    <a href="/dashboard" className="block p-3 mt-12 rounded-lg text-gray-500 hover:text-gray-300 transition-colors">← Exit Admin</a>
                </nav>
            </aside>
            <main className="flex-1 p-8 text-white max-h-screen overflow-auto">
                <div className="max-w-7xl mx-auto">
                    {children}
                </div>
            </main>
        </div>
    )
}
