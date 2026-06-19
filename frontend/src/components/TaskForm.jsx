import { useState } from 'react'

export const TASKS = [
  { key: 'pr_review',       label: 'PR Review',         icon: '🔍' },
  { key: 'bug_scan',        label: 'Bug Scan',           icon: '🐛' },
  { key: 'explain_code',    label: 'Explain Code',       icon: '💡' },
  { key: 'refactor',        label: 'Refactor',           icon: '♻️'  },
  { key: 'similar_bugs',    label: 'Similar Bugs',       icon: '🔎' },
  { key: 'generate_tests',  label: 'Generate Tests',     icon: '🧪' },
  { key: 'migration_plan',  label: 'Migration Plan',     icon: '🗺️'  },
  { key: 'impact_analysis', label: 'Impact Analysis',    icon: '📊' },
  { key: 'version_bump',    label: 'Version Bumps',      icon: '📦' },
  { key: 'license_check',   label: 'License Check',      icon: '⚖️'  },
  { key: 'vuln_scan',       label: 'Vuln Scan',          icon: '🛡️'  },
]

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  )
}

const INPUT = "w-full px-3 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors"
const SELECT = INPUT + " cursor-pointer"
const TEXTAREA = INPUT + " resize-none"

export default function TaskForm({ task, repo, onSubmit, loading }) {
  const [fields, setFields] = useState({})
  const set = (k, v) => setFields(prev => ({ ...prev, [k]: v }))

  function handleSubmit(e) {
    e.preventDefault()
    const repoUrl  = repo?.url  || ''
    const repoName = repo?.full_name?.split('/')[1] || ''

    const payloads = {
      pr_review:       { repo: repoUrl, pr_number: parseInt(fields.pr_number || 0) },
      bug_scan:        { repo: repoUrl, scope: fields.scope || '.' },
      explain_code:    { repo: repoUrl, target: fields.target || '' },
      refactor:        { repos: [repoName], target: fields.target || '', goal: fields.goal || '' },
      similar_bugs:    { repos: [repoName], known_bug: fields.known_bug || '' },
      generate_tests:  { repo: repoUrl, target: fields.target || '', framework: fields.framework || 'auto-detect' },
      migration_plan:  { repo: repoUrl, component: fields.component || '', target_stack: fields.target_stack || '' },
      impact_analysis: { repos: [repoName], symbol: fields.symbol || '', proposed_change: fields.proposed_change || '' },
      version_bump:    { repos: [repoName], ecosystem: fields.ecosystem || 'all' },
      license_check:   { repos: [repoName], project_type: fields.project_type || 'commercial' },
      vuln_scan:       { repos: [repoName], images: [], alert_threshold: fields.alert_threshold || 'HIGH' },
    }
    onSubmit({ user_story: task, ...payloads[task] })
  }

  if (!task) return null

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {task === 'pr_review' && (
        <Field label="Pull Request Number">
          <input type="number" className={INPUT} placeholder="e.g. 142"
            value={fields.pr_number || ''} onChange={e => set('pr_number', e.target.value)} required />
        </Field>
      )}

      {task === 'bug_scan' && (
        <Field label="Scope (file, directory, or '.' for full repo)">
          <input type="text" className={INPUT} placeholder="app/services"
            value={fields.scope || ''} onChange={e => set('scope', e.target.value)} />
        </Field>
      )}

      {(task === 'explain_code' || task === 'generate_tests') && (
        <Field label="Target (file path or function name)">
          <input type="text" className={INPUT} placeholder="app/services/payment.py"
            value={fields.target || ''} onChange={e => set('target', e.target.value)} required />
        </Field>
      )}

      {task === 'generate_tests' && (
        <Field label="Test Framework">
          <select className={SELECT} value={fields.framework || 'auto-detect'} onChange={e => set('framework', e.target.value)}>
            <option value="auto-detect">Auto-detect</option>
            <option value="pytest">pytest</option>
            <option value="vitest">vitest</option>
            <option value="xunit">xUnit</option>
          </select>
        </Field>
      )}

      {task === 'refactor' && (
        <>
          <Field label="Target (file or class)">
            <input type="text" className={INPUT} placeholder="app/services/auth.py"
              value={fields.target || ''} onChange={e => set('target', e.target.value)} required />
          </Field>
          <Field label="Refactoring Goal">
            <textarea rows={3} className={TEXTAREA} placeholder="Extract authentication logic into a separate service..."
              value={fields.goal || ''} onChange={e => set('goal', e.target.value)} required />
          </Field>
        </>
      )}

      {task === 'similar_bugs' && (
        <Field label="Describe the Known Bug">
          <textarea rows={4} className={TEXTAREA}
            placeholder="e.g. User input is passed directly to a SQL query without parameterisation..."
            value={fields.known_bug || ''} onChange={e => set('known_bug', e.target.value)} required />
        </Field>
      )}

      {task === 'migration_plan' && (
        <>
          <Field label="Component (file or service name)">
            <input type="text" className={INPUT} placeholder="app/legacy/email_service.py"
              value={fields.component || ''} onChange={e => set('component', e.target.value)} required />
          </Field>
          <Field label="Target Stack">
            <input type="text" className={INPUT} placeholder="e.g. FastAPI + Redis queue"
              value={fields.target_stack || ''} onChange={e => set('target_stack', e.target.value)} required />
          </Field>
        </>
      )}

      {task === 'impact_analysis' && (
        <>
          <Field label="Symbol (fully qualified name)">
            <input type="text" className={INPUT} placeholder="app.services.IPaymentService.charge"
              value={fields.symbol || ''} onChange={e => set('symbol', e.target.value)} required />
          </Field>
          <Field label="Proposed Change">
            <textarea rows={3} className={TEXTAREA} placeholder="Add required parameter: idempotency_key: str"
              value={fields.proposed_change || ''} onChange={e => set('proposed_change', e.target.value)} required />
          </Field>
        </>
      )}

      {task === 'version_bump' && (
        <Field label="Ecosystem">
          <select className={SELECT} value={fields.ecosystem || 'all'} onChange={e => set('ecosystem', e.target.value)}>
            <option value="all">All</option>
            <option value="npm">npm</option>
            <option value="pip">pip</option>
            <option value="nuget">NuGet</option>
          </select>
        </Field>
      )}

      {task === 'license_check' && (
        <Field label="Project Type">
          <select className={SELECT} value={fields.project_type || 'commercial'} onChange={e => set('project_type', e.target.value)}>
            <option value="commercial">Commercial</option>
            <option value="internal">Internal</option>
            <option value="open-source">Open Source</option>
          </select>
        </Field>
      )}

      {task === 'vuln_scan' && (
        <Field label="Alert Threshold">
          <select className={SELECT} value={fields.alert_threshold || 'HIGH'} onChange={e => set('alert_threshold', e.target.value)}>
            <option value="CRITICAL">Critical only</option>
            <option value="HIGH">High and above</option>
            <option value="MEDIUM">Medium and above</option>
          </select>
        </Field>
      )}

      <button
        type="submit"
        disabled={loading || !repo}
        className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm
                   disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="30 60" />
            </svg>
            Running agent…
          </>
        ) : (
          '▶  Run Agent'
        )}
      </button>

      {!repo && (
        <p className="text-center text-xs text-slate-500">Select a repository first</p>
      )}
    </form>
  )
}
