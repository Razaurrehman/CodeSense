import { Github } from 'lucide-react'

export default function LoginPage({ onLogin }) {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="text-center max-w-md w-full">

        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <span className="text-5xl">🧠</span>
        </div>

        <h1 className="text-4xl font-bold text-white mb-2">CodeSense</h1>
        <p className="text-slate-400 text-lg mb-10">
          AI-powered code intelligence for your repositories
        </p>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {[
            'PR Review', 'Bug Detection', 'CVE Scanning',
            'Test Generation', 'Impact Analysis', 'Code Explanation',
          ].map(f => (
            <span key={f}
              className="px-3 py-1 bg-slate-800 border border-slate-700 rounded-full text-xs text-slate-300">
              {f}
            </span>
          ))}
        </div>

        {/* Login button */}
        <button
          onClick={onLogin}
          className="flex items-center justify-center gap-3 w-full py-3.5 px-6 rounded-xl
                     bg-white hover:bg-gray-100 text-gray-900 font-semibold text-sm
                     transition-colors shadow-lg"
        >
          <Github size={20} />
          Continue with GitHub
        </button>

        <p className="text-slate-600 text-xs mt-6">
          Your code never leaves your server. All analysis runs locally via Ollama.
        </p>
      </div>
    </div>
  )
}
