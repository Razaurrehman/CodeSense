import { useState, useEffect } from 'react'
import { Search, Lock, Globe, GitBranch, ChevronDown } from 'lucide-react'

export default function RepoSelector({ selected, onSelect }) {
  const [repos,   setRepos]   = useState([])
  const [query,   setQuery]   = useState('')
  const [open,    setOpen]    = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch('/api/v1/auth/repos', { credentials: 'include' })
      .then(r => r.json())
      .then(data => { setRepos(Array.isArray(data) ? data : []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = repos.filter(r =>
    r.full_name.toLowerCase().includes(query.toLowerCase()) ||
    (r.description || '').toLowerCase().includes(query.toLowerCase())
  )

  function handleSelect(repo) {
    onSelect(repo)
    setOpen(false)
    setQuery('')
  }

  return (
    <div className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-800 border border-slate-700
                   rounded-xl text-left hover:border-slate-600 transition-colors"
      >
        {selected ? (
          <div className="flex items-center gap-2 min-w-0">
            {selected.private ? <Lock size={13} className="text-slate-400 flex-shrink-0" /> : <Globe size={13} className="text-slate-400 flex-shrink-0" />}
            <span className="text-white text-sm truncate">{selected.full_name}</span>
            {selected.language && (
              <span className="text-xs text-slate-500 flex-shrink-0">{selected.language}</span>
            )}
          </div>
        ) : (
          <span className="text-slate-400 text-sm">Select a repository…</span>
        )}
        <ChevronDown size={15} className={`text-slate-400 flex-shrink-0 ml-2 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl z-50 overflow-hidden">
          {/* Search */}
          <div className="p-2 border-b border-slate-700">
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search repositories…"
                autoFocus
                className="w-full pl-8 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg
                           text-sm text-white placeholder:text-slate-500
                           focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* List */}
          <div className="max-h-72 overflow-y-auto">
            {loading && (
              <div className="px-4 py-6 text-center text-slate-400 text-sm">Loading repositories…</div>
            )}
            {!loading && filtered.length === 0 && (
              <div className="px-4 py-6 text-center text-slate-400 text-sm">No repositories found</div>
            )}
            {filtered.map(repo => (
              <button
                key={repo.full_name}
                onClick={() => handleSelect(repo)}
                className="w-full px-4 py-3 flex items-start gap-3 hover:bg-slate-700 transition-colors text-left"
              >
                <div className="mt-0.5 flex-shrink-0">
                  {repo.private
                    ? <Lock size={13} className="text-slate-400" />
                    : <Globe size={13} className="text-slate-400" />}
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-white font-medium truncate">{repo.full_name}</p>
                  {repo.description && (
                    <p className="text-xs text-slate-400 truncate mt-0.5">{repo.description}</p>
                  )}
                  {repo.language && (
                    <div className="flex items-center gap-1 mt-1">
                      <GitBranch size={10} className="text-slate-500" />
                      <span className="text-xs text-slate-500">{repo.language}</span>
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
