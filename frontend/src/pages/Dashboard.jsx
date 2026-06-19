import { useState } from 'react'
import { LogOut } from 'lucide-react'
import RepoSelector  from '../components/RepoSelector'
import TaskForm, { TASKS } from '../components/TaskForm'
import ResultPanel   from '../components/ResultPanel'

export default function Dashboard({ user, onLogout }) {
  const [selectedRepo, setSelectedRepo] = useState(null)
  const [activeTask,   setActiveTask]   = useState(TASKS[0].key)
  const [loading,      setLoading]      = useState(false)
  const [result,       setResult]       = useState(null)
  const [error,        setError]        = useState(null)

  async function handleRun(payload) {
    setLoading(true)
    setResult(null)
    setError(null)

    const ENDPOINTS = {
      pr_review:       '/api/v1/review',
      bug_scan:        '/api/v1/scan/bugs',
      explain_code:    '/api/v1/explain',
      refactor:        '/api/v1/refactor',
      similar_bugs:    '/api/v1/scan/similar',
      generate_tests:  '/api/v1/tests/generate',
      migration_plan:  '/api/v1/migrate',
      impact_analysis: '/api/v1/impact',
      version_bump:    '/api/v1/deps/update',
      license_check:   '/api/v1/licenses',
      vuln_scan:       '/api/v1/scan/vuln',
    }

    try {
      const res = await fetch(ENDPOINTS[payload.user_story], {
        method:      'POST',
        credentials: 'include',
        headers:     { 'Content-Type': 'application/json' },
        body:        JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Request failed')
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const activeTaskMeta = TASKS.find(t => t.key === activeTask)

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">

      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">🧠</span>
          <span className="font-bold text-white">CodeSense</span>
        </div>
        <div className="flex items-center gap-3">
          <img src={user.avatar_url} alt={user.login}
            className="w-7 h-7 rounded-full border border-slate-700" />
          <span className="text-sm text-slate-300">{user.name || user.login}</span>
          <button onClick={onLogout}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors px-2 py-1.5 rounded-lg hover:bg-slate-800">
            <LogOut size={13} />
            Sign out
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">

        {/* Left sidebar — task list */}
        <aside className="w-52 flex-shrink-0 border-r border-slate-800 py-4 overflow-y-auto">
          <p className="px-4 mb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
            Workflows
          </p>
          {TASKS.map(task => (
            <button
              key={task.key}
              onClick={() => { setActiveTask(task.key); setResult(null); setError(null) }}
              className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                ${activeTask === task.key
                  ? 'bg-blue-600/20 text-blue-400 border-r-2 border-blue-500'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}`}
            >
              <span className="text-base">{task.icon}</span>
              <span className="font-medium">{task.label}</span>
            </button>
          ))}
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto space-y-6">

            {/* Repo selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                Repository
              </label>
              <RepoSelector selected={selectedRepo} onSelect={setSelectedRepo} />
            </div>

            {/* Active task title */}
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <span className="text-xl">{activeTaskMeta?.icon}</span>
              <h2 className="text-base font-semibold text-white">{activeTaskMeta?.label}</h2>
            </div>

            {/* Task form */}
            <TaskForm
              task={activeTask}
              repo={selectedRepo}
              onSubmit={handleRun}
              loading={loading}
            />

            {/* Result */}
            <ResultPanel result={result} error={error} />

          </div>
        </main>
      </div>
    </div>
  )
}
