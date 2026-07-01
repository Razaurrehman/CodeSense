import { useState, useEffect, useRef } from 'react'
import { Search, Lock, Globe, GitBranch, ChevronDown, X, Check } from 'lucide-react'

export default function RepoSelector({ selected, onSelect }) {
  const [repos,   setRepos]   = useState([])
  const [query,   setQuery]   = useState('')
  const [open,    setOpen]    = useState(false)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    fetch('/api/v1/auth/repos', { credentials: 'include' })
      .then(r => r.json())
      .then(data => { setRepos(Array.isArray(data) ? data : []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filtered = repos.filter(r =>
    r.full_name.toLowerCase().includes(query.toLowerCase()) ||
    (r.description || '').toLowerCase().includes(query.toLowerCase())
  )

  function isSelected(repo) {
    return selected.some(r => r.full_name === repo.full_name)
  }

  function toggleRepo(repo) {
    if (isSelected(repo)) {
      onSelect(selected.filter(r => r.full_name !== repo.full_name))
    } else {
      onSelect([...selected, repo])
    }
  }

  function removeRepo(repo, e) {
    e.stopPropagation()
    onSelect(selected.filter(r => r.full_name !== repo.full_name))
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-800 border border-slate-700
                   rounded-xl text-left hover:border-slate-600 transition-colors min-h-[48px]"
      >
        {selected.length === 0 ? (
          <span className="text-slate-400 text-sm">Select repositories…</span>
        ) : (
          <div className="flex flex-wrap gap-1.5 flex-1 mr-2">
            {selected.map(repo => (
              <span
                key={repo.full_name}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-600/20 border border-blue-500/30
                           text-blue-300 text-xs rounded-md"
              >
                {repo.private ? <Lock size={10} /> : <Globe size={10} />}
                <span className="truncate max-w-[140px]">{repo.full_name}</span>
                <span
                  role="button"
                  tabIndex={0}
                  onClick={e => removeRepo(repo, e)}
                  onKeyDown={e => e.key === 'Enter' && removeRepo(repo, e)}
                  className="ml-0.5 hover:text-white cursor-pointer"
                >
                  <X size={10} />
                </span>
              </span>
            ))}
          </div>
        )}
        <ChevronDown size={15} className={`text-slate-400 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {selected.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">{selected.length} repo{selected.length > 1 ? 's' : ''} selected</p>
      )}

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

          {/* Actions */}
          {selected.length > 0 && (
            <div className="px-4 py-2 border-b border-slate-700 flex items-center justify-between">
              <span className="text-xs text-slate-400">{selected.length} selected</span>
              <button
                type="button"
                onClick={() => onSelect([])}
                className="text-xs text-slate-500 hover:text-white transition-colors"
              >
                Clear all
              </button>
            </div>
          )}

          {/* List */}
          <div className="max-h-72 overflow-y-auto">
            {loading && (
              <div className="px-4 py-6 text-center text-slate-400 text-sm">Loading repositories…</div>
            )}
            {!loading && filtered.length === 0 && (
              <div className="px-4 py-6 text-center text-slate-400 text-sm">No repositories found</div>
            )}
            {filtered.map(repo => {
              const checked = isSelected(repo)
              return (
                <button
                  key={repo.full_name}
                  type="button"
                  onClick={() => toggleRepo(repo)}
                  className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-700 transition-colors text-left
                    ${checked ? 'bg-blue-600/10' : ''}`}
                >
                  {/* Checkbox */}
                  <div className={`w-4 h-4 rounded flex-shrink-0 border flex items-center justify-center transition-colors
                    ${checked ? 'bg-blue-600 border-blue-600' : 'border-slate-500'}`}>
                    {checked && <Check size={11} className="text-white" strokeWidth={3} />}
                  </div>

                  <div className="flex-shrink-0">
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
              )
            })}
          </div>

          {/* Done button */}
          <div className="p-2 border-t border-slate-700">
            <button
              type="button"
              onClick={() => { setOpen(false); setQuery('') }}
              className="w-full py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm text-white transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
