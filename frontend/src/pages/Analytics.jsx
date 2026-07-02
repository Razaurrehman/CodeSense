import { useState, useEffect } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  LineChart, Line, CartesianGrid, PieChart, Pie, Cell,
} from 'recharts'

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high:     '#f97316',
  medium:   '#eab308',
  low:      '#22c55e',
}

function StatCard({ label, value, sub, color = 'text-white' }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

const TASK_SHORT = {
  bug_scan:        'Bugs',
  vuln_scan:       'Vulns',
  explain_code:    'Explain',
  refactor:        'Refactor',
  similar_bugs:    'Similar',
  generate_tests:  'Tests',
  migration_plan:  'Migrate',
  impact_analysis: 'Impact',
  version_bump:    'Versions',
  license_check:   'Licenses',
  pr_review:       'PR Review',
}

export default function Analytics({ onRunScan }) {
  const [summary,  setSummary]  = useState(null)
  const [byRepo,   setByRepo]   = useState([])
  const [overTime, setOverTime] = useState([])
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [s, r, t] = await Promise.all([
          fetch('/api/v1/stats/summary',  { credentials: 'include' }).then(x => x.json()),
          fetch('/api/v1/stats/by-repo',  { credentials: 'include' }).then(x => x.json()),
          fetch('/api/v1/stats/over-time',{ credentials: 'include' }).then(x => x.json()),
        ])
        setSummary(s)
        setByRepo(r.repos || [])
        setOverTime(t.data || [])
      } catch (e) {
        console.error('Analytics load error', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  /* Build flat bar-chart data: one entry per repo with tasks as bars */
  const repoBarData = byRepo.map(r => {
    const entry = { repo: r.repo }
    r.tasks.forEach(t => {
      entry[TASK_SHORT[t.task] ?? t.task] = t.total
    })
    return entry
  })

  /* Pie chart: severity breakdown from summary */
  const pieData = summary ? [
    { name: 'Critical', value: summary.critical, color: SEVERITY_COLORS.critical },
    { name: 'High',     value: summary.high,     color: SEVERITY_COLORS.high },
    { name: 'Medium',   value: summary.medium,   color: SEVERITY_COLORS.medium },
    { name: 'Low',      value: summary.low,      color: SEVERITY_COLORS.low },
  ].filter(d => d.value > 0) : []

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 text-sm">
        Loading analytics…
      </div>
    )
  }

  return (
    <div className="p-6 space-y-8 max-w-5xl mx-auto">

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Analytics Dashboard</h2>
        <button
          onClick={onRunScan}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          ▶ Run a Scan
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Runs"     value={summary?.total_runs}     />
        <StatCard label="Repos Scanned"  value={summary?.repos_scanned}  />
        <StatCard label="Total Findings" value={summary?.total_findings} color="text-yellow-400" />
        <StatCard label="Critical"       value={summary?.critical}       color="text-red-400"
          sub={`High: ${summary?.high ?? 0}  Med: ${summary?.medium ?? 0}  Low: ${summary?.low ?? 0}`} />
      </div>

      {/* Findings by repo — stacked bar */}
      {repoBarData.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wide">
            Findings by Repository
          </h3>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={repoBarData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="repo" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#f1f5f9' }}
                  itemStyle={{ color: '#94a3b8' }}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                {Object.values(TASK_SHORT).map((name, i) => {
                  const hue = (i * 37) % 360
                  return (
                    <Bar key={name} dataKey={name} stackId="a"
                      fill={`hsl(${hue},60%,55%)`} radius={i === 0 ? [4, 4, 0, 0] : undefined} />
                  )
                })}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">

        {/* Severity pie */}
        {pieData.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wide">
              Severity Breakdown
            </h3>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col items-center">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {pieData.map(entry => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                    itemStyle={{ color: '#94a3b8' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-2 flex-wrap justify-center">
                {pieData.map(d => (
                  <span key={d.name} className="flex items-center gap-1.5 text-xs text-slate-400">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
                    {d.name}: {d.value}
                  </span>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Scans over time */}
        {overTime.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wide">
              Scans Over Time
            </h3>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={overTime} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                    labelStyle={{ color: '#f1f5f9' }}
                    itemStyle={{ color: '#94a3b8' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                  <Line type="monotone" dataKey="runs"     stroke="#60a5fa" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="findings" stroke="#f97316" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        )}

      </div>

      {/* Per-repo table */}
      {byRepo.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wide">
            Repo Detail
          </h3>
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/60">
                <tr>
                  {['Repo', 'Task', 'Runs', 'Total', 'Critical', 'High', 'Medium', 'Low'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {byRepo.flatMap(r =>
                  r.tasks.map((t, i) => (
                    <tr key={`${r.repo}-${t.task}`} className="border-t border-slate-800 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-2.5 text-slate-300 font-mono text-xs">{i === 0 ? r.repo : ''}</td>
                      <td className="px-4 py-2.5 text-slate-400 text-xs">{TASK_SHORT[t.task] ?? t.task}</td>
                      <td className="px-4 py-2.5 text-slate-400">{t.runs}</td>
                      <td className="px-4 py-2.5 font-semibold text-yellow-400">{t.total}</td>
                      <td className="px-4 py-2.5 text-red-400">{t.critical}</td>
                      <td className="px-4 py-2.5 text-orange-400">{t.high}</td>
                      <td className="px-4 py-2.5 text-yellow-300">{t.medium}</td>
                      <td className="px-4 py-2.5 text-green-400">{t.low}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {byRepo.length === 0 && (
        <div className="text-center py-16 space-y-4">
          <p className="text-slate-500 text-sm">No scan results yet.</p>
          <button
            onClick={onRunScan}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            ▶ Run a Scan Now
          </button>
        </div>
      )}

    </div>
  )
}
