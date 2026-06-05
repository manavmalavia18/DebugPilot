import { useEffect, useRef, useState } from "react"
import { api } from "../api"

export default function FollowUpChat({ incidentId }) {
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
    <div className="shrink-0 border-t border-border bg-void/80">
      <div className="border-b border-border px-3 py-2">
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted">Follow-up chat</p>
        <p className="text-[11px] text-muted">Ask about the diagnosis, commands, or fix</p>
      </div>

      <div className="max-h-36 overflow-y-auto px-3 py-2 space-y-2">
        {messages.length === 0 && !loading && (
          <p className="font-mono text-[11px] text-neutral-500">
            e.g. &quot;Why localhost fails in K8s?&quot; or &quot;Show the YAML change&quot;
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`rounded border px-2 py-1.5 text-[12px] leading-relaxed ${
              msg.role === "user"
                ? "border-border bg-panel text-neutral-300"
                : "border-accent/25 bg-accent/5 text-neutral-200"
            }`}
          >
            <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
              {msg.role === "user" ? "you" : "debugpilot"}
            </span>
            <p className="mt-0.5 whitespace-pre-wrap">{msg.content}</p>
          </div>
        ))}
        {loading && (
          <p className="animate-pulse font-mono text-[11px] text-info">thinking...</p>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="px-3 pb-1 font-mono text-[11px] text-red-300">{error}</p>
      )}

      <div className="flex gap-2 border-t border-border p-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
          placeholder="Ask a follow-up..."
          disabled={loading}
          className="min-w-0 flex-1 border border-border bg-black px-2 py-1.5 font-mono text-[12px] text-neutral-200 outline-none focus:border-accent"
        />
        <button
          type="button"
          onClick={send}
          disabled={loading || !input.trim()}
          className="shrink-0 border border-accent bg-accent/15 px-3 py-1.5 font-mono text-[11px] text-accent hover:bg-accent/25 disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  )
}
