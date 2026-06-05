import { useEffect, useRef, useState } from "react"
import { api } from "../api"

export default function FollowUpChat({ incidentId, fullHeight = false }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!incidentId) {
      setMessages([])
      return undefined
    }
    let cancelled = false
    setError("")
    api
      .get(`/incidents/${incidentId}/messages`)
      .then((res) => {
        if (!cancelled) setMessages(res.data)
      })
      .catch(() => {
        if (!cancelled) setMessages([])
      })
    return () => {
      cancelled = true
    }
  }, [incidentId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  const send = async () => {
    const text = input.trim()
    if (!text || !incidentId || loading) return
    setLoading(true)
    setError("")
    setInput("")
    const optimistic = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimistic])
    try {
      const res = await api.post(`/incidents/${incidentId}/chat`, { message: text })
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimistic.id),
        { ...optimistic, id: `user-${Date.now()}` },
        res.data.message,
      ])
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id))
      setInput(text)
      setError(err.response?.data?.detail || err.message || "Chat failed")
    } finally {
      setLoading(false)
    }
  }

  if (!incidentId) return null

  return (
    <div
      className={`flex flex-col border border-accent/40 bg-panel ${
        fullHeight ? "h-full min-h-[320px] xl:min-h-0" : "min-h-[280px] shrink-0"
      }`}
    >
      <div className="shrink-0 border-b border-accent/30 bg-accent/5 px-4 py-3">
        <h2 className="font-mono text-sm font-semibold text-accent">Follow-up chat</h2>
        <p className="mt-0.5 text-xs text-muted">
          Ask about the diagnosis, Helm changes, or commands
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && !loading && (
          <div className="rounded border border-dashed border-border bg-void/50 px-3 py-4 text-center">
            <p className="font-mono text-xs text-neutral-400">No messages yet</p>
            <p className="mt-2 font-mono text-[11px] leading-relaxed text-muted">
              Try: &quot;What should REDIS_URL be in the Helm chart?&quot;
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`rounded border px-3 py-2.5 text-[13px] leading-relaxed ${
              msg.role === "user"
                ? "border-border bg-void text-neutral-200"
                : "border-accent/30 bg-accent/8 text-neutral-100"
            }`}
          >
            <span
              className={`font-mono text-[10px] font-semibold uppercase tracking-wider ${
                msg.role === "user" ? "text-muted" : "text-accent"
              }`}
            >
              {msg.role === "user" ? "You" : "DebugPilot"}
            </span>
            <p className="mt-1.5 whitespace-pre-wrap">{msg.content}</p>
          </div>
        ))}
        {loading && (
          <p className="animate-pulse font-mono text-sm text-info">DebugPilot is thinking...</p>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="shrink-0 px-4 pb-2 font-mono text-xs text-red-300">{error}</p>
      )}

      <div className="shrink-0 space-y-2 border-t border-border bg-void/40 p-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
          placeholder="Ask a follow-up... (Enter to send, Shift+Enter for newline)"
          disabled={loading}
          rows={3}
          className="w-full resize-none border border-border bg-black px-3 py-2.5 font-mono text-[13px] leading-relaxed text-neutral-200 outline-none focus:border-accent"
        />
        <button
          type="button"
          onClick={send}
          disabled={loading || !input.trim()}
          className="w-full border border-accent bg-accent/20 py-2.5 font-mono text-sm font-semibold text-accent transition-colors hover:bg-accent/30 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Sending..." : "Send message"}
        </button>
      </div>
    </div>
  )
}
