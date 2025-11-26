import React, { useState } from 'react'

export default function SnippetLibrary({ snippets, onCreate, onSearch }) {
  const [language, setLanguage] = useState('')
  const [prompt, setPrompt] = useState('')
  const [newSnippet, setNewSnippet] = useState({ language: '', category: 'example', text: '' })

  const handleCreate = (event) => {
    event.preventDefault()
    if (!newSnippet.language || !newSnippet.text) return
    onCreate(newSnippet)
    setNewSnippet({ language: '', category: 'example', text: '' })
  }

  const handleSearch = (event) => {
    event.preventDefault()
    if (language && prompt) {
      onSearch(language, prompt)
    }
  }

  return (
    <div className="card">
      <div className="header">
        <h3>Snippet Library</h3>
        <p className="badge">local-only</p>
      </div>

      <form onSubmit={handleCreate} className="grid cols-2" style={{ alignItems: 'flex-start' }}>
        <div className="grid" style={{ gap: '0.5rem' }}>
          <input
            placeholder="Language"
            value={newSnippet.language}
            onChange={(e) => setNewSnippet({ ...newSnippet, language: e.target.value })}
          />
          <select value={newSnippet.category} onChange={(e) => setNewSnippet({ ...newSnippet, category: e.target.value })}>
            <option value="example">Example</option>
            <option value="tip">Tip</option>
            <option value="error">Error</option>
          </select>
        </div>
        <textarea
          placeholder="Snippet body"
          value={newSnippet.text}
          onChange={(e) => setNewSnippet({ ...newSnippet, text: e.target.value })}
        />
        <button type="submit">Add snippet</button>
      </form>

      <form onSubmit={handleSearch} className="small-grid" style={{ marginTop: '1rem' }}>
        <input placeholder="Filter language" value={language} onChange={(e) => setLanguage(e.target.value)} />
        <input placeholder="Search text" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <button type="submit" className="secondary">Search</button>
      </form>

      <div className="list" style={{ marginTop: '1rem' }}>
        {snippets.map((snippet, index) => (
          <div key={`${snippet.source}-${index}`} className="entry">
            <div className="entry-meta">
              <span className="badge">{snippet.language}</span>
              <span className="badge">{snippet.category}</span>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{snippet.text}</pre>
            <div className="entry-meta">
              <span className="tag">{snippet.source}</span>
            </div>
          </div>
        ))}
        {!snippets.length && <p className="badge">No snippets loaded</p>}
      </div>
    </div>
  )
}
