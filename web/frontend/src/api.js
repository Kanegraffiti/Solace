const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || response.statusText)
  }
  if (response.headers.get('content-type')?.includes('application/json')) {
    return response.json()
  }
  return response
}

export async function downloadExport(token, format = 'markdown') {
  const response = await apiRequest(`/api/entries/export?format=${format}`, { token })
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = response.url.split('/').pop()
  a.click()
  window.URL.revokeObjectURL(url)
}

export { API_BASE }
