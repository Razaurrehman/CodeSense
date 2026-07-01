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

export default function TaskForm({ task, repos, onSubmit, loading }) {
  const [fields, setFields] = useState({})
  const set = (k, v) => setFields(prev => ({ ...prev, [k]: v }))

  // first selected repo for single-repo workflows
  const primaryRepo = repos[0] || null
  const primaryUrl  = primaryRepo?.clone_url || primaryRepo?.url || ''
  const repoNames   = repos.map(r => r.full_name?.split('/')[1]).filter(Boolean)

  function handleSubmit(e) {
    e.preventDefault()

    const payloads = {
      pr_review:       { repo: primaryUrl },
      bug_scan:        { repo: primaryUrl, scope: '.' },
      explain_code:    { repo: primaryUrl },
      refactor:        { repos: repoNames },
      similar_bugs:    { repos: repoNames },
      generate_tests:  { repo: primaryUrl },
      migration_plan:  { repo: primaryUrl },
      impact_analysis: { repos: repoNames },
      version_bump:    { repos: repoNames },
      license_check:   { repos: repoNames },
      vuln_scan:       { repo: primaryUrl },
    }
    onSubmit({ user_story: task, ...payloads[task] })
  }

  if (!task) return null

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {task === 'pr_review' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Automatically reviews all open pull requests in the selected repository.
        </div>
      )}

      {task === 'bug_scan' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the full repository for bugs and security issues.
        </div>
      )}

      {task === 'explain_code' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Analyses the complete repository and explains the codebase architecture, key modules, and data flow.
        </div>
      )}

      {task === 'generate_tests' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository, auto-detects the test framework, and generates tests for untested functions and classes.
        </div>
      )}

      {task === 'refactor' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository and identifies refactoring opportunities across all source files.
        </div>
      )}

      {task === 'similar_bugs' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository to detect recurring bug patterns and similar issues across all source files.
        </div>
      )}

      {task === 'migration_plan' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository and generates a phased migration plan identifying legacy components and modernisation opportunities.
        </div>
      )}

      {task === 'impact_analysis' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository and maps high-impact symbols, dependencies, and change-risk hotspots.
        </div>
      )}

      {task === 'version_bump' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository, auto-detects all package manifests, and recommends safe dependency version bumps.
        </div>
      )}

      {task === 'license_check' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository for license files and dependency manifests, then flags compliance risks.
        </div>
      )}

      {task === 'vuln_scan' && (
        <div className="px-4 py-3 bg-blue-600/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
          Scans the complete repository for known CVEs and security vulnerabilities in all dependencies.
        </div>
      )}

      <button
        type="submit"
        disabled={loading || repos.length === 0}
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

      {repos.length === 0 && (
        <p className="text-center text-xs text-slate-500">Select at least one repository first</p>
      )}
    </form>
  )
}
