import { useState, useEffect } from 'react'
import { LogOut, ScanLine } from 'lucide-react'
import { TASKS } from '../components/TaskForm'
import RepoScans     from './RepoScans'
import JobAnalytics  from './JobAnalytics'
import WorkflowTable from './WorkflowTable'

function parseHash() {
  const h = window.location.hash.replace(/^#\/?/, '')
  if (h.startsWith('scans/'))    return { page: 'job-analytics', uuid: h.slice(6) }
  if (h === 'scans')             return { page: 'scans' }
  if (h.startsWith('workflow/')) return { page: 'workflow', task: h.slice(9) }
  return { page: 'workflow', task: TASKS[0].key }
}

export default function Dashboard({ user, onLogout }) {
  const [route, setRoute] = useState(parseHash)

  useEffect(() => {
    function onHash() { setRoute(parseHash()) }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  function navigate(hash) {
    window.location.hash = hash
    setRoute(parseHash())
  }

  const page = route.page
  const activeTaskMeta = TASKS.find(t => t.key === route.task) || TASKS[0]

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

        {/* Left sidebar */}
        <aside className="w-52 flex-shrink-0 border-r border-slate-800 py-4 overflow-y-auto">

          <button
            onClick={() => navigate('#scans')}
            className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors mb-2
              ${(page === 'scans' || page === 'job-analytics')
                ? 'bg-blue-600/20 text-blue-400 border-r-2 border-blue-500'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}`}
          >
            <ScanLine size={15} />
            <span className="font-medium">Repo Scans</span>
          </button>

          <p className="px-4 mb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
            Workflows
          </p>

          {TASKS.map(task => (
            <button
              key={task.key}
              onClick={() => navigate(`#workflow/${task.key}`)}
              className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                ${page === 'workflow' && route.task === task.key
                  ? 'bg-blue-600/20 text-blue-400 border-r-2 border-blue-500'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}`}
            >
              <span className="text-base">{task.icon}</span>
              <span className="font-medium">{task.label}</span>
            </button>
          ))}
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          {page === 'job-analytics' ? (
            <JobAnalytics uuid={route.uuid} onBack={() => navigate('#scans')} />
          ) : page === 'scans' ? (
            <RepoScans />
          ) : (
            <WorkflowTable
              key={activeTaskMeta.key}
              taskKey={activeTaskMeta.key}
              taskLabel={activeTaskMeta.label}
              taskIcon={activeTaskMeta.icon}
            />
          )}
        </main>
      </div>
    </div>
  )
}
