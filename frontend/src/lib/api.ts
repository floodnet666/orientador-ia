const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
    const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Request failed')
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
    list: () => request<unknown[]>('/api/projects/'),

    create: (body: { title: string; domain_area: string; academic_level: string; human_guidelines?: string }) =>
        request<unknown>('/api/projects/', { method: 'POST', body: JSON.stringify(body) }),

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
        return fetch(`${API_BASE}/api/empirical/${projectId}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData,
        }).then(res => res.json())
    }
}

// ── Almas (Genesis & Tooling) ────────────────────────────────────────────────

export const almasApi = {
    genesis: (prompt: string) => request<unknown>('/api/almas/genesis', {
        method: 'POST',
        body: JSON.stringify({ prompt }),
    }),

    execute: (code: string, context: Record<string, unknown> = {}) =>
        request<any>('/api/almas/execute', {
            method: 'POST',
            body: JSON.stringify({ code, context }),
        }),
}
