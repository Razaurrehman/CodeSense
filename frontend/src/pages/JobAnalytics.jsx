import { useState, useEffect, useRef } from 'react'
import {
  ArrowLeft, CheckCircle2, XCircle, Clock, Loader2, Download, List, X,
  ChevronDown, ChevronRight,
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell,
  PieChart, Pie, Legend,
} from 'recharts'

const TASK_LABELS = {
  bug_scan:        'Bug Scan',
  vuln_scan:       'Vulnerability Scan',
  explain_code:    'Explain Code',
  refactor:        'Refactoring',
  similar_bugs:    'Similar Bugs',
  generate_tests:  'Generate Tests',
  migration_plan:  'Migration Plan',
  impact_analysis: 'Impact Analysis',
  version_bump:    'Version Bumps',
  license_check:   'License Check',
  pr_review:       'PR Review',
}

const BAR_COLORS = [
  '#3b82f6','#f97316','#22c55e','#a855f7','#eab308',
  '#ec4899','#14b8a6','#f43f5e','#6366f1','#84cc16',
]

function parseFindingCount(output = '') {
  return (output.match(/^### \[(BUG|CVE|REF|PAT|IMP|LIC|VULN|TEST|MIG|VER)-\d+\]/gm) || []).length
}

function parseFindings(output = '') {
  const findings = []
  const blocks = output.split(/^(?=### \[)/m).filter(Boolean)
  for (const block of blocks) {
    const lines = block.trim().split('\n')
    const header = lines[0].replace(/^### /, '').trim()
    if (/^\[(BUG|CVE|REF|PAT|IMP|LIC|VULN|TEST|MIG|VER)-\d+\]/.test(header)) {
      const body = lines.slice(1).join('\n').trim()
      findings.push({ header, body })
    }
  }
  return findings
}

function FindingsDrawer({ scanLabel, findings, rawOutput, onClose }) {
  const [rawOpen, setRawOpen] = useState(false)

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-md"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <div className="relative w-full max-w-md bg-slate-900 border-l border-slate-700 flex flex-col h-full shadow-2xl animate-slide-in-right">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <List size={14} className="text-blue-400 flex-shrink-0" />
            <span className="font-semibold text-white text-sm truncate">{scanLabel}</span>
            <span className="text-xs text-slate-500 flex-shrink-0">
              {findings.length} finding{findings.length !== 1 ? 's' : ''}
            </span>
          </div>
          <button onClick={onClose} className="ml-3 text-slate-400 hover:text-white transition-colors flex-shrink-0">
            <X size={16} />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">
          {findings.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-10">No structured findings in this scan output.</p>
          ) : (
            <ul className="space-y-4">
              {findings.map((f, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-yellow-400 font-mono break-all">{f.header}</p>
                    {f.body && (
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed whitespace-pre-wrap">{f.body}</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* Collapsible raw output */}
          {rawOutput && (
            <div className="border border-slate-700 rounded-lg overflow-hidden">
              <button
                onClick={() => setRawOpen(o => !o)}
                className="w-full flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700/80 transition-colors text-xs font-medium text-slate-300"
              >
                {rawOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                Raw Output
              </button>
              {rawOpen && (
                <pre className="px-4 py-3 text-[11px] text-slate-400 font-mono leading-relaxed whitespace-pre-wrap break-words bg-slate-950/60 overflow-y-auto">
                  {rawOutput}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function StatusBadge({ status }) {
  const cfg = {
    queued:  { cls: 'bg-slate-800 text-slate-400',     icon: <Clock size={11} />,                            label: 'In Queue'     },
    running: { cls: 'bg-blue-900/40 text-blue-400',    icon: <Loader2 size={11} className="animate-spin" />, label: 'In Progress'  },
    done:    { cls: 'bg-green-900/30 text-green-400',  icon: <CheckCircle2 size={11} />,                     label: 'Completed'    },
    failed:  { cls: 'bg-red-900/30 text-red-400',      icon: <XCircle size={11} />,                          label: 'Failed'       },
  }[status] || { cls: 'bg-slate-800 text-slate-400', icon: null, label: status }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

function StatCard({ label, value, color = 'text-white', sub }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

export default function JobAnalytics({ uuid, onBack }) {
  const [job,     setJob]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [modal,   setModal]   = useState(null)  // { label, findings }

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch(`/api/v1/jobs/by-uuid/${uuid}`, { credentials: 'include' })
      .then(r => { if (!r.ok) throw new Error('Job not found'); return r.json() })
      .then(d => setJob(d))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [uuid])

  if (loading) return (
    <div className="flex items-center justify-center h-full text-slate-400 gap-2 text-sm">
      <Loader2 size={16} className="animate-spin" /> Loading analytics…
    </div>
  )

  if (error) return (
    <div className="p-10 text-center">
      <p className="text-red-400 mb-4">{error}</p>
      <button onClick={onBack} className="text-slate-400 hover:text-white text-sm underline">← Back to Repo Scans</button>
    </div>
  )

  const results = job.results || []

  const scanStats = results.map((r, i) => ({
    label:    TASK_LABELS[r.scan_type] || r.scan_type,
    key:      r.scan_type,
    status:   r.status,
    findings: r.status === 'done' ? parseFindingCount(r.output) : null,
    output:   r.output || '',
    color:    BAR_COLORS[i % BAR_COLORS.length],
  }))

  const totalFindings = scanStats.reduce((s, r) => s + (r.findings ?? 0), 0)
  const doneCount     = results.filter(r => r.status === 'done').length
  const failedCount   = results.filter(r => r.status === 'failed').length
  const pendingCount  = results.filter(r => ['pending','running'].includes(r.status)).length

  const barData = scanStats.filter(r => (r.findings ?? 0) > 0)

  const pieData = [
    { name: 'Completed', value: doneCount,    fill: '#22c55e' },
    { name: 'Failed',    value: failedCount,  fill: '#ef4444' },
    { name: 'Pending',   value: pendingCount, fill: '#64748b' },
  ].filter(d => d.value > 0)

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">

      {modal && (
        <FindingsDrawer
          scanLabel={modal.label}
          findings={modal.findings}
          rawOutput={modal.rawOutput}
          onClose={() => setModal(null)}
        />
      )}

      {/* Back + header */}
      <div>
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-4">
          <ArrowLeft size={13} /> Back to Repo Scans
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white">{job.repo_name}</h2>
            <p className="text-xs font-mono text-slate-500 mt-0.5 select-all">{job.uuid}</p>
            <p className="text-xs text-slate-500 mt-1">
              Created {fmtDate(job.created_at)}
              {job.completed_at && <> · Completed {fmtDate(job.completed_at)}</>}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <StatusBadge status={job.status} />
            {job.pdf_ready && (
              <a href={`/api/v1/jobs/${job.id}/pdf`} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-medium rounded-lg transition-colors">
                <Download size={12} /> Download PDF
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Scans"    value={job.total_scans}  />
        <StatCard label="Completed"      value={doneCount}        color="text-green-400" />
        <StatCard label="Failed"         value={failedCount}      color="text-red-400" />
        <StatCard label="Findings Found" value={totalFindings}    color="text-yellow-400"
          sub={pendingCount > 0 ? `${pendingCount} scan${pendingCount !== 1 ? 's' : ''} still running` : undefined} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">

        {/* Bar chart — findings per scan (spans 2 cols) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-slate-300 mb-4">Findings by Scan Type</p>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 50 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  angle={-35}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#f1f5f9' }}
                  formatter={v => [v, 'Findings']}
                />
                <Bar dataKey="findings" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => <Cell key={entry.key} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
              {pendingCount > 0 ? 'Scans still in progress…' : 'No findings detected.'}
            </div>
          )}
        </div>

        {/* Pie chart — scan status breakdown */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-slate-300 mb-4">Scan Status</p>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="45%"
                  outerRadius={75}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {pieData.map(entry => <Cell key={entry.name} fill={entry.fill} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 11, color: '#94a3b8' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">No data yet.</div>
          )}
        </div>
      </div>

      {/* Per-scan results table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-800">
          <p className="text-sm font-semibold text-slate-300">Scan Results</p>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-800/60">
            <tr>
              {['#', 'Scan Type', 'Status', 'Findings', ''].map(h => (
                <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scanStats.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-500 text-sm">No scan results yet.</td></tr>
            )}
            {scanStats.map((r, i) => {
              const findings = parseFindings(r.output)
              return (
                <tr key={r.key} className="border-t border-slate-800 hover:bg-slate-800/20 transition-colors">
                  <td className="px-5 py-3.5 text-slate-500 text-xs">{i + 1}</td>
                  <td className="px-5 py-3.5">
                    <span className="flex items-center gap-2 text-slate-200 text-xs font-medium">
                      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: r.color }} />
                      {r.label}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-5 py-3.5">
                    {r.findings === null ? (
                      <span className="text-slate-500 text-xs">—</span>
                    ) : r.findings > 0 ? (
                      <span className="text-yellow-400 font-semibold text-sm">{r.findings}</span>
                    ) : (
                      <span className="text-green-400 text-xs">None detected</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    {r.status === 'done' ? (
                      <button
                        onClick={() => setModal({ label: r.label, findings, rawOutput: r.output })}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-medium rounded-lg transition-colors"
                      >
                        <List size={11} /> View Findings
                      </button>
                    ) : (
                      <span className="text-slate-600 text-xs">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

    </div>
  )
}
