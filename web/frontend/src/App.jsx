import React, { useEffect, useState } from 'react'
import EntryList from './components/EntryList'
import SnippetLibrary from './components/SnippetLibrary'
import { apiRequest, downloadExport, API_BASE } from './api'

const entryTypes = [
  { value: 'diary', label: 'Diary' },
  { value: 'notes', label: 'Notes' },
  { value: 'todo', label: 'To-Do' },
  { value: 'quote', label: 'Quote' }
]

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('solaceToken') || '')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [entries, setEntries] = useState([])
  const [snippets, setSnippets] = useState([])
  const [tags, setTags] = useState([])
  const [filterTag, setFilterTag] = useState('')
  const [newEntry, setNewEntry] = useState({ content: '', entry_type: 'diary', tags: '' })
  const [status, setStatus] = useState('Ready')
  const [meta, setMeta] = useState(null)

  const authenticated = Boolean(token)

  const handleLogin = async (event) => {
    event.preventDefault()
    try {
      const response = await apiRequest('/api/auth/login', { method: 'POST', body: { password } })
      localStorage.setItem('solaceToken', response.token)
      setToken(response.token)
      setAuthError('')
      setStatus('Logged in')
    } catch (error) {
      setAuthError(error.message)
      setStatus('Login failed')
    }
  }

  const loadData = async (tag) => {
    if (!token) return
    setStatus('Loading entries…')
    const params = tag ? `?tag=${encodeURIComponent(tag)}` : ''
    const [entryData, tagData, snippetData, metaData] = await Promise.all([
      apiRequest(`/api/entries${params}`, { token }),
      apiRequest('/api/tags', { token }),
      apiRequest('/api/snippets', { token }),
      apiRequest('/api/meta', { token })
    ])
    setEntries(entryData)
    setTags(tagData)
    setSnippets(snippetData)
    setMeta(metaData)
    setStatus('Ready')
  }

  useEffect(() => {
    if (token) {
      loadData(filterTag).catch((error) => setStatus(error.message))
    }
  }, [token])

  const handleCreateEntry = async (event) => {
    event.preventDefault()
    if (!newEntry.content) return
    const payload = {
      content: newEntry.content,
      entry_type: newEntry.entry_type,
      tags: newEntry.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
    }
    await apiRequest('/api/entries', { method: 'POST', body: payload, token })
    setNewEntry({ content: '', entry_type: 'diary', tags: '' })
    loadData(filterTag)
  }

  const handleCreateSnippet = async (snippet) => {
    await apiRequest('/api/snippets', { method: 'POST', body: snippet, token })
    loadData(filterTag)
  }

  const handleSearchSnippet = async (language, prompt) => {
    const results = await apiRequest(`/api/snippets/search?language=${language}&prompt=${encodeURIComponent(prompt)}`, { token })
    setSnippets(results)
  }

  const handleExport = async () => {
    setStatus('Building export…')
    await downloadExport(token)
    setStatus('Export ready')
  }

  const handleTagFilter = (tag) => {
    setFilterTag(tag)
    loadData(tag)
  }

  const handleLogout = () => {
    setToken('')
    localStorage.removeItem('solaceToken')
    setEntries([])
    setSnippets([])
    setTags([])
    setStatus('Logged out')
  }

  if (!authenticated) {
    return (
      <div className="app-shell">
        <div className="card">
          <h2>Sign in to local Solace</h2>
          <p className="notice">Local-only. Keep the browser and API on the same machine.</p>
          <form onSubmit={handleLogin} className="grid" style={{ gap: '0.75rem' }}>
            <input
              type="password"
              placeholder="Solace password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button type="submit">Login</button>
          </form>
          {authError && <p className="badge" style={{ marginTop: '0.5rem' }}>{authError}</p>}
          <p className="footer">API base: {API_BASE} · Uses the same password configured for Solace.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <div className="header">
        <div>
          <h1>Solace Web</h1>
          <p className="notice">Local-only workspace. Do not expose beyond localhost.</p>
        </div>
        <div className="grid" style={{ gap: '0.35rem', textAlign: 'right' }}>
          <button className="secondary" onClick={handleLogout}>Logout</button>
          <span className="badge">{status}</span>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <div className="header">
            <h3>New entry</h3>
            <button className="secondary" onClick={handleExport}>Export markdown</button>
          </div>
          <form className="grid" style={{ gap: '0.75rem' }} onSubmit={handleCreateEntry}>
            <textarea
              placeholder="What happened today?"
              value={newEntry.content}
              onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
            />
            <div className="small-grid">
              <select
                value={newEntry.entry_type}
                onChange={(e) => setNewEntry({ ...newEntry, entry_type: e.target.value })}
              >
                {entryTypes.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <input
                placeholder="Tags (comma separated)"
                value={newEntry.tags}
                onChange={(e) => setNewEntry({ ...newEntry, tags: e.target.value })}
              />
              <button type="submit">Save entry</button>
            </div>
          </form>
        </div>

        <SnippetLibrary snippets={snippets} onCreate={handleCreateSnippet} onSearch={handleSearchSnippet} />
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <div className="header">
          <h3>Diary</h3>
          <div className="small-grid">
            <select value={filterTag} onChange={(e) => handleTagFilter(e.target.value)}>
              <option value="">All tags</option>
              {tags.map((tag) => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </select>
            <button className="secondary" onClick={() => loadData(filterTag)}>Refresh</button>
          </div>
        </div>
        <EntryList entries={entries} />
      </div>

      {meta && (
        <p className="footer">
          Local storage: {meta.storage_root} · Config: {meta.config_path} · Password enabled: {meta.password_required}
        </p>
      )}
    </div>
  )
}
