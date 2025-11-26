import React from 'react'

export default function EntryList({ entries }) {
  if (!entries.length) {
    return <p className="badge">No entries yet</p>
  }
  return (
    <div className="list">
      {entries.map((entry) => (
        <div className="entry" key={entry.identifier}>
          <div className="entry-meta">
            <span>{entry.date} at {entry.time}</span>
            <span className="badge">{entry.entry_type}</span>
          </div>
          <p>{entry.content}</p>
          <div className="entry-meta">
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {(entry.tags || []).map((tag) => (
                <span className="tag" key={tag}>#{tag}</span>
              ))}
            </div>
            {entry.encrypted && <span className="badge">encrypted</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
