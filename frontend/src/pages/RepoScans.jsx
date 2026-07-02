import { useState, useEffect, useRef } from 'react'
import {
  X, Download, Plus, ChevronDown, Loader2, CheckCircle2, XCircle,
  Clock, Play, ChevronLeft, ChevronRight, BarChart2, Search, Globe, Lock, GitBranch,
} from 'lucide-react'


const PAGE_SIZE_OPTIONS = [10, 25, 50]

const ALL_SCAN_TYPES = [
  { key: 'bug_scan',        label: 'Bug Scan'           },
  { key: 'vuln_scan',       label: 'Vulnerability Scan' },
  { key: 'explain_code',    label: 'Explain Code'       },
  { key: 'refactor',        label: 'Refactoring'        },
  { key: 'similar_bugs',    label: 'Similar Bugs'       },
  { key: 'generate_tests',  label: 'Generate Tests'     },
  { key: 'migration_plan',  label: 'Migration Plan'     },
  { key: 'impact_analysis', label: 'Impact Analysis'    },
  { key: 'version_bump',    label: 'Version Bumps'      },
  { key: 'license_check',   label: 'License Check'      },
]

// ── Status badge ──────────────────────────────────────────────────

function StatusBadge({ status, completed, total }) {
  if (status === 'queued') return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400">
      <Clock size={11} /> In Queue
    </span>
  )
  if (status === 'running') return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-900/40 text-blue-400">
      <Loader2 size={11} className="animate-spin" /> In Progress ({completed}/{total})
    </span>
  )
  if (status === 'done') return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-900/30 text-green-400">
      <CheckCircle2 size={11} /> Completed
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-900/30 text-red-400">
      <XCircle size={11} /> Failed
    </span>
  )
}

// ── Multi-select dropdown ─────────────────────────────────────────

function MultiSelect({ selected, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const allSelected = selected.length === ALL_SCAN_TYPES.length
  const toggle    = key => onChange(selected.includes(key) ? selected.filter(k => k !== key) : [...selected, key])
  const toggleAll = () => onChange(allSelected ? [] : ALL_SCAN_TYPES.map(t => t.key))

  const label = allSelected ? 'All scan types'
    : selected.length === 0 ? 'Select scan types…'
    : `${selected.length} selected`

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 hover:border-slate-500 transition-colors"
      >
        <span className={selected.length === 0 ? 'text-slate-500' : ''}>{label}</span>
        <ChevronDown size={14} className={`text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg shadow-xl overflow-hidden">
          <label className="flex items-center gap-2.5 px-3 py-2.5 hover:bg-slate-700 cursor-pointer border-b border-slate-700">
            <input type="checkbox" checked={allSelected} onChange={toggleAll} className="w-4 h-4 rounded accent-blue-500" />
            <span className="text-sm font-semibold text-white">All</span>
          </label>
          {ALL_SCAN_TYPES.map(t => (
            <label key={t.key} className="flex items-center gap-2.5 px-3 py-2 hover:bg-slate-700 cursor-pointer">
              <input type="checkbox" checked={selected.includes(t.key)} onChange={() => toggle(t.key)} className="w-4 h-4 rounded accent-blue-500" />
              <span className="text-sm text-slate-200">{t.label}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Single-select repo dropdown ───────────────────────────────────

function RepoDropdown({ value, onChange }) {
  const [repos,   setRepos]   = useState([])
  const [query,   setQuery]   = useState('')
  const [open,    setOpen]    = useState(false)
  const [loading, setLoading] = useState(true)
  const ref = useRef(null)

  useEffect(() => {
    fetch('/api/v1/auth/repos', { credentials: 'include' })
      .then(r => r.json())
      .then(d => setRepos(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    function handler(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = repos.filter(r =>
    r.full_name.toLowerCase().includes(query.toLowerCase()) ||
    (r.description || '').toLowerCase().includes(query.toLowerCase())
  )

  function select(repo) {
    onChange(repo.clone_url || repo.html_url, repo)
    setOpen(false)
    setQuery('')
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-sm hover:border-slate-500 transition-colors min-h-[42px]"
      >
        {value ? (
          <span className="flex items-center gap-2 text-slate-200 truncate">
            <Globe size={13} className="text-slate-400 flex-shrink-0" />
            <span className="truncate">{value.full_name}</span>
          </span>
        ) : (
          <span className="text-slate-500">Select a repository…</span>
        )}
        <ChevronDown size={14} className={`text-slate-400 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
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
                className="w-full pl-8 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* List */}
          <div className="max-h-64 overflow-y-auto">
            {loading && (
              <div className="px-4 py-6 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
                <Loader2 size={14} className="animate-spin" /> Loading…
              </div>
            )}
            {!loading && filtered.length === 0 && (
              <div className="px-4 py-6 text-center text-slate-500 text-sm">No repositories found</div>
            )}
            {filtered.map(repo => (
              <button
                key={repo.full_name}
                type="button"
                onClick={() => select(repo)}
                className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-700 transition-colors text-left
                  ${value?.full_name === repo.full_name ? 'bg-blue-600/10' : ''}`}
              >
                {repo.private
                  ? <Lock size={13} className="text-slate-400 flex-shrink-0" />
                  : <Globe size={13} className="text-slate-400 flex-shrink-0" />}
                <div className="min-w-0">
                  <p className="text-sm text-white font-medium truncate">{repo.full_name}</p>
                  {repo.description && (
                    <p className="text-xs text-slate-400 truncate mt-0.5">{repo.description}</p>
                  )}
                  {repo.language && (
                    <span className="inline-flex items-center gap-1 mt-0.5">
                      <GitBranch size={10} className="text-slate-500" />
                      <span className="text-xs text-slate-500">{repo.language}</span>
                    </span>
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

// ── Create modal ──────────────────────────────────────────────────

function CreateModal({ onClose, onCreate }) {
  const [selectedRepo, setSelectedRepo] = useState(null)   // full repo object
  const [repoUrl,      setRepoUrl]      = useState('')
  const [scanTypes,    setScanTypes]    = useState(ALL_SCAN_TYPES.map(t => t.key))
  const [submitting,   setSubmitting]   = useState(false)
  const [error,        setError]        = useState(null)

  function handleRepoSelect(url, repo) {
    setRepoUrl(url)
    setSelectedRepo(repo)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!repoUrl)          { setError('Please select a repository'); return }
    if (!scanTypes.length) { setError('Select at least one scan type'); return }
    setSubmitting(true)
    setError(null)
    try {
      const res  = await fetch('/api/v1/jobs', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl, scan_types: scanTypes }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to create job')
      onCreate(data)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-xl shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <h2 className="text-base font-semibold text-white">Scan Repository</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Repository</label>
            <RepoDropdown value={selectedRepo} onChange={handleRepoSelect} />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Scan Types</label>
            <MultiSelect selected={scanTypes} onChange={setScanTypes} />
          </div>
          {error && (
            <p className="text-sm text-red-400 bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">{error}</p>
          )}
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={submitting}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed rounded-lg transition-colors">
              {submitting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {submitting ? 'Queuing…' : 'Run Scan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ── Main page ─────────────────────────────────────────────────────

export default function RepoScans() {
  const [jobs,     setJobs]     = useState([])
  const [loading,  setLoading]  = useState(true)
  const [modal,    setModal]    = useState(false)
  const [page,     setPage]     = useState(1)
  const [pageSize, setPageSize] = useState(10)

  async function loadJobs() {
    try {
      const res  = await fetch('/api/v1/jobs', { credentials: 'include' })
      const data = await res.json()
      setJobs(data.jobs || [])
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => {
    loadJobs()
    const id = setInterval(loadJobs, 6000)
    return () => clearInterval(id)
  }, [])

  function handleCreate(job) { setJobs(prev => [job, ...prev]); setPage(1) }

  const scanTypeLabel = types =>
    types.length === ALL_SCAN_TYPES.length ? 'All (10)' : `${types.length} scan${types.length !== 1 ? 's' : ''}`

  const totalPages = Math.max(1, Math.ceil(jobs.length / pageSize))
  const safePage   = Math.min(page, totalPages)
  const pageJobs   = jobs.slice((safePage - 1) * pageSize, safePage * pageSize)
  function goTo(p) { setPage(Math.max(1, Math.min(p, totalPages))) }
  function pageNumbers() {
    const delta = 2, range = []
    for (let i = Math.max(1, safePage - delta); i <= Math.min(totalPages, safePage + delta); i++) range.push(i)
    return range
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Repository Scans</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Submit a repository for a full multi-scan analysis and download the PDF report when complete.
          </p>
        </div>
        <button onClick={() => setModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors">
          <Plus size={15} /> Scan Repository
        </button>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/60">
            <tr>
              {['UUID', 'Repository', 'Created', 'Scans', 'Status', 'Download', 'Analytics'].map(h => (
                <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-sm">
                <Loader2 size={18} className="animate-spin mx-auto mb-2" /> Loading jobs…
              </td></tr>
            )}

            {!loading && jobs.length === 0 && (
              <tr><td colSpan={7} className="px-5 py-16 text-center">
                <p className="text-slate-500 text-sm mb-3">No scan jobs yet.</p>
                <button onClick={() => setModal(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors">
                  <Plus size={14} /> Scan a Repository
                </button>
              </td></tr>
            )}

            {pageJobs.map(job => (
              <tr key={job.id} className="border-t border-slate-800 hover:bg-slate-800/20 transition-colors">

                {/* UUID */}
                <td className="px-5 py-3.5">
                  <span className="font-mono text-xs text-slate-500 select-all">{job.uuid}</span>
                </td>

                {/* Repo */}
                <td className="px-5 py-3.5">
                  <p className="font-medium text-slate-200">{job.repo_name}</p>
                  <p className="text-xs text-slate-500 font-mono mt-0.5 truncate max-w-xs">{job.repo_url}</p>
                </td>

                {/* Created */}
                <td className="px-5 py-3.5 text-slate-400 text-xs whitespace-nowrap">{fmtDate(job.created_at)}</td>

                {/* Scans */}
                <td className="px-5 py-3.5 text-slate-400 text-xs">{scanTypeLabel(job.scan_types)}</td>

                {/* Status */}
                <td className="px-5 py-3.5">
                  <StatusBadge status={job.status} completed={job.completed_scans} total={job.total_scans} />
                </td>

                {/* Download */}
                <td className="px-5 py-3.5">
                  {job.pdf_ready ? (
                    <a href={`/api/v1/jobs/${job.id}/pdf`} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-medium rounded-lg transition-colors">
                      <Download size={12} /> PDF
                    </a>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-slate-600 text-xs font-medium rounded-lg cursor-not-allowed">
                      <Download size={12} /> PDF
                    </span>
                  )}
                </td>

                {/* Analytics */}
                <td className="px-5 py-3.5">
                  {job.status === 'done' || job.status === 'failed' ? (
                    <button
                      onClick={() => { window.location.hash = `#scans/${job.uuid}` }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-violet-700/40 hover:bg-violet-600/60 text-violet-300 text-xs font-medium rounded-lg transition-colors"
                    >
                      <BarChart2 size={12} /> Analytics
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-slate-600 text-xs font-medium rounded-lg cursor-not-allowed">
                      <BarChart2 size={12} /> Analytics
                    </span>
                  )}
                </td>

              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination footer */}
        {!loading && jobs.length > 0 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800 bg-slate-900/60">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                {jobs.length} job{jobs.length !== 1 ? 's' : ''} · showing {(safePage - 1) * pageSize + 1}–{Math.min(safePage * pageSize, jobs.length)}
              </span>
              <select value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
                className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-md px-2 py-1 focus:outline-none focus:border-slate-500">
                {PAGE_SIZE_OPTIONS.map(n => <option key={n} value={n}>{n} / page</option>)}
              </select>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={() => goTo(safePage - 1)} disabled={safePage === 1}
                className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                <ChevronLeft size={14} />
              </button>
              {safePage > 3 && (
                <>
                  <button onClick={() => goTo(1)} className="w-7 h-7 rounded-md text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors">1</button>
                  {safePage > 4 && <span className="text-slate-600 text-xs px-1">…</span>}
                </>
              )}
              {pageNumbers().map(n => (
                <button key={n} onClick={() => goTo(n)}
                  className={`w-7 h-7 rounded-md text-xs font-medium transition-colors ${n === safePage ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>
                  {n}
                </button>
              ))}
              {safePage < totalPages - 2 && (
                <>
                  {safePage < totalPages - 3 && <span className="text-slate-600 text-xs px-1">…</span>}
                  <button onClick={() => goTo(totalPages)} className="w-7 h-7 rounded-md text-xs text-slate-400 hover:text-white hover:bg-slate-700 transition-colors">{totalPages}</button>
                </>
              )}
              <button onClick={() => goTo(safePage + 1)} disabled={safePage === totalPages}
                className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {modal && <CreateModal onClose={() => setModal(false)} onCreate={handleCreate} />}
    </div>
  )
}
