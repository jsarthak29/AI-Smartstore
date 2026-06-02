import { useState, useRef, useEffect } from 'react'
import { aiApi } from '../api/resources.js'

export default function ChatPanel() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [messages, busy])

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setInput('')
    setBusy(true)
    try {
      const res = await aiApi.chat(next)
      setMessages([...next, { role: 'assistant', content: res.reply, tools: res.tool_calls || [] }])
    } catch (e) {
      setMessages([...next, { role: 'assistant', content: `⚠️ ${e.response?.data?.detail || 'Chat failed'}`, tools: [] }])
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 bg-brand-600 text-white px-4 py-3 rounded-full shadow-lg hover:bg-brand-700"
      >
        💬 Ask AI
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 max-w-[90vw] h-[36rem] flex flex-col bg-white shadow-2xl rounded-lg border border-slate-200 z-50">
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-200">
        <div className="font-semibold text-sm">SmartStore AI Assistant</div>
        <button className="text-slate-400 hover:text-slate-700" onClick={() => setOpen(false)}>×</button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3 text-sm bg-slate-50">
        {messages.length === 0 && (
          <div className="text-xs text-slate-400">
            Try: <i>"Which products will run out in 7 days?"</i> · <i>"Draft a PO for our lowest-stock items"</i>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            <div className={`inline-block px-3 py-2 rounded-lg max-w-[85%] whitespace-pre-wrap ${m.role === 'user' ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200'}`}>
              {m.content}
            </div>
            {m.tools?.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {m.tools.map((t, j) => (
                  <span key={j} title={JSON.stringify(t.args)} className="badge bg-indigo-100 text-indigo-800 font-mono">🛠 {t.name}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="text-slate-400 text-xs animate-pulse">Assistant is thinking…</div>
        )}
      </div>
      <div className="px-3 py-2 border-t border-slate-200">
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="Ask about stock, suppliers, POs…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
          />
          <button className="btn-primary" disabled={busy} onClick={send}>Send</button>
        </div>
      </div>
    </div>
  )
}
