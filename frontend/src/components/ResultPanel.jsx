import ReactMarkdown from 'react-markdown'
import { Copy, CheckCircle } from 'lucide-react'
import { useState } from 'react'

export default function ResultPanel({ result, error }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(result?.output || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-5">
        <p className="text-red-400 font-semibold text-sm mb-1">Agent error</p>
        <p className="text-red-300/80 text-xs whitespace-pre-wrap">{error}</p>
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-800">
        <div className="flex items-center gap-2">
          <CheckCircle size={14} className="text-green-400" />
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
            {result.user_story?.replace(/_/g, ' ')}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <Copy size={12} />
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Content */}
      <div className="p-5 prose prose-invert prose-sm max-w-none overflow-auto max-h-[60vh]
                      prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700
                      prose-code:text-blue-300 prose-headings:text-white
                      prose-strong:text-white prose-a:text-blue-400">
        <ReactMarkdown>{result.output}</ReactMarkdown>
      </div>
    </div>
  )
}
