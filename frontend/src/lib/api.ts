const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

function getToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('token')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const token = getToken()
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers || {}),
    }

    // Dynamic base URL to bypass Next.js proxy in development
    let baseUrl = API_BASE
    if (!baseUrl && typeof window !== 'undefined') {
        baseUrl = `${window.location.protocol}//${window.location.hostname}:8000`
    }

    const res = await fetch(`${baseUrl}${path}`, { ...init, headers })
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        const errorMsg = Array.isArray(err.detail) ? err.detail.map((e: any) => `${e.loc?.join('.')}: ${e.msg}`).join(', ') : err.detail
        throw new Error(errorMsg || 'Request failed')
    }
    return res.json()
}


// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
    register: (body: { email: string; password: string; full_name: string; academic_level: string }) =>
        request<{ access_token: string }>('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(body),
        }),

    login: (body: { email: string; password: string }) =>
        request<{ access_token: string }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify(body),
        }),

    me: () => request<{ id: string; email: string; full_name: string; academic_level: string }>('/api/auth/me'),
}

// ── Projects ─────────────────────────────────────────────────────────────────

export const projectsApi = {
    list: () => request<unknown[]>('/api/projects'),

    create: (body: { title: string; domain_area: string; academic_level: string; human_guidelines?: string }) =>
        request<unknown>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),

    get: (id: string) => request<unknown>(`/api/projects/${id}`),

    update: (id: string, body: Partial<{ title: string; domain_area: string; status: string; human_guidelines: string }>) =>
        request<unknown>(`/api/projects/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),

    delete: (id: string) => request<unknown>(`/api/projects/${id}`, { method: 'DELETE' }),

    match: (id: string, raw_idea: string) =>
        request<unknown>(`/api/projects/${id}/match`, {
            method: 'POST',
            body: JSON.stringify({ raw_idea }),
        }),

    selectAlmas: (id: string, body: { theoretical_alma_id: string; methodological_alma_id: string }) =>
        request<unknown>(`/api/projects/${id}/select-almas`, {
            method: 'POST',
            body: JSON.stringify(body),
        }),

    getCanvas: (id: string) => request<unknown>(`/api/projects/${id}/canvas`),

    patchCanvas: (id: string, field: string, value: unknown) =>
        request<unknown>(`/api/projects/${id}/canvas`, {
            method: 'PATCH',
            body: JSON.stringify({ field, value }),
        }),
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export const chatApi = {
    history: (projectId: string) => request<unknown[]>(`/api/chat/${projectId}/history`),
}

// ── Empirical Data (Mesa-Redonda) ──────────────────────────────────────────

export const empiricalApi = {
    list: (projectId: string) => request<string[]>(`/api/empirical/${projectId}/documents`),

    upload: (projectId: string, file: File) => {
        const formData = new FormData()
        formData.append('file', file)
        
        let url = API_BASE
        if (!url && typeof window !== 'undefined') {
            url = `${window.location.protocol}//${window.location.hostname}:8000`
        }

        return fetch(`${url}/api/empirical/${projectId}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData,
        }).then(res => res.json())
    },



    getStatus: (projectId: string, filename: string) => 
        request<{ filename: string; status: string }>(`/api/empirical/${projectId}/status/${filename}`),

    delete: (projectId: string, filename: string) => 
        request<{ message: string }>(`/api/empirical/${projectId}/documents/${filename}`, { method: 'DELETE' }),
}

// ── Almas (Genesis & Tooling) ────────────────────────────────────────────────

export const almasApi = {
    genesis: (prompt: string) =>
        request<any>('/api/almas/genesis', {
            method: 'POST',
            body: JSON.stringify({ description: prompt }),
        }),


    execute: (code: string, context: Record<string, unknown> = {}) =>
        request<any>('/api/almas/execute', {
            method: 'POST',
            body: JSON.stringify({ code, context }),
        }),
}

// ── Admin ────────────────────────────────────────────────────────────────────

export const adminApi = {
    // Users
    getUsers: () => request<any[]>('/api/admin/users'),
    createUser: (body: any) => request<any>('/api/admin/users', { method: 'POST', body: JSON.stringify(body) }),
    deleteUser: (id: string) => request<any>(`/api/admin/users/${id}`, { method: 'DELETE' }),
    resetPassword: (id: string, body: any) => request<any>(`/api/admin/users/${id}/reset-password`, { method: 'POST', body: JSON.stringify(body) }),

    // Almas
    getAlmas: () => request<any[]>('/api/admin/almas'),
    createAlma: (body: any) => request<any>('/api/admin/almas', { method: 'POST', body: JSON.stringify(body) }),
    updateAlma: (id: string, body: any) => request<any>(`/api/admin/almas/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    deleteAlma: (id: string) => request<any>(`/api/admin/almas/${id}`, { method: 'DELETE' }),

    // Alma Prompts
    updatePrompt: (id: string, body: any) => request<any>(`/api/admin/almas/${id}/prompt`, { method: 'POST', body: JSON.stringify(body) }),
    rollbackPrompt: (almaId: string, historyId: string) => request<any>(`/api/admin/almas/${almaId}/rollback/${historyId}`, { method: 'POST' }),
    getPromptHistory: (id: string) => request<any[]>(`/api/admin/almas/${id}/history`),

    // Observability
    getMetrics: () => request<any>('/api/admin/metrics'),

    // Ollama
    getOllamaModels: () => request<string[]>('/api/admin/ollama/models'),
}
