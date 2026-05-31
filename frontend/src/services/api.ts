const API_BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  getCount: () => request('/count'),
  getCountHistory: (hours = 24) => request(`/count/history?hours=${hours}`),
  getCameras: () => request('/cameras'),
  getIdentities: () => request('/identities'),
  getEvents: (cameraId?: string, limit = 100) =>
    request(`/events?${cameraId ? `camera_id=${cameraId}&` : ''}limit=${limit}`),
  getBlacklist: () => request('/blacklist'),
  addBlacklist: (entry: { global_id?: string; description?: string; reason?: string }) =>
    request('/blacklist', { method: 'POST', body: JSON.stringify(entry) }),
  removeBlacklist: (id: number) =>
    request(`/blacklist/${id}`, { method: 'DELETE' }),
  login: (username: string, password: string) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    }),
  register: (username: string, password: string, role: string) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, role }),
    }),
  getUsers: () => request('/auth/users'),
  getMe: () => request('/auth/me'),
}
