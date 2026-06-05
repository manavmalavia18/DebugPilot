import { useEffect, useRef, useState } from "react"
import { api } from "../api"

const SECTION_ORDER = ["SUMMARY", "FIX", "COMMANDS", "WARNINGS"]

function stripMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*]\s+/gm, "- ")
}

function parseStructuredMessage(content) {
  const normalized = stripMarkdown(content.trim())
  const lines = normalized.split("\n")
  const rawSections = []
  let current = null

  for (const line of lines) {
    const header = line.match(/^(SUMMARY|FIX|COMMANDS|WARNINGS):\s*(.*)$/i)
    if (header) {
      if (current) rawSections.push(current)
      current = { label: header[1].toUpperCase(), body: header[2].trim() }
      continue
    }
    if (current && line.trim()) {
      current.body = current.body ? `${current.body}\n${line.trim()}` : line.trim()
    }
  }
  if (current) rawSections.push(current)
  if (!rawSections.length) return null

  return rawSections
    .filter((section) => SECTION_ORDER.includes(section.label))
    .sort((a, b) => SECTION_ORDER.indexOf(a.label) - SECTION_ORDER.indexOf(b.label))
    .map((section) => ({
      label: section.label.charAt(0) + section.label.slice(1).toLowerCase(),
      body: section.body,
    }))
}

function parseListLines(body) {
  return body
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*]\s*/, ""))
}

function ChatSection({ label, body, warn = false }) {
  const lines = parseListLines(body)
  const isCommandBlock = label === "Commands"
  const isList = label === "Fix" || label === "Warnings" || isCommandBlock

  return (
    <div
      className={`border p-2.5 ${
        warn
          ? "border-warn/30 bg-warn/5"
          : label === "Fix"
            ? "border-accent/30 bg-accent/5"
            : "border-border bg-void"
      }`}
    >
      <p className="font-mono text-[10px] uppercase tracking-wider text-muted">{label}</p>
      {isList ? (
        <ul className="mt-1.5 space-y-1.5">
          {lines.map((line) => (
            <li
              key={line}
              className={`text-sm leading-relaxed ${
                isCommandBlock ? "border border-border bg-black px-2 py-1.5 font-mono text-[12px] text-accent" : "text-neutral-200"
              }`}
            >
              {isCommandBlock ? line : `• ${line}`}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5 text-sm leading-relaxed text-neutral-200">{body}</p>
      )}
    </div>
  )
}

function ChatMessageBody({ content }) {
  const sections = parseStructuredMessage(content)

  if (sections) {
    return (
      <div className="mt-2 space-y-2">
        {sections.map((section) => (
          <ChatSection
            key={section.label}
            label={section.label}
            body={section.body}
            warn={section.label === "Warnings"}
          />
        ))}
      </div>
    )
  }

  return (
    <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-neutral-200">
      {stripMarkdown(content)}
    </p>
  )
}

export default function FollowUpChat({ incidentId, fullHeight = false, floating = false, onSaveResolution }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [savingResolution, setSavingResolution] = useState(false)
  const bottomRef = useRef(null)

  const lastAssistant = [...messages].reverse().find((msg) => msg.role === "assistant")

  const extractFixText = (content) => {
    const sections = parseStructuredMessage(content)
    const fix = sections?.find((section) => section.label === "Fix")
    if (fix?.body) return fix.body.replace(/^[-*]\s*/gm, "").trim()
    return stripMarkdown(content).trim()
  }

  const saveLastReplyAsResolution = async () => {
    if (!lastAssistant || !onSaveResolution || savingResolution) return
    const text = extractFixText(lastAssistant.content)
    if (!text) return
    setSavingResolution(true)
    setError("")
    try {
      await onSaveResolution(text)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to save resolution")
    } finally {
      setSavingResolution(false)
    }
  }

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
      className={`flex h-full min-h-0 flex-col ${
        floating ? "bg-transparent" : "border border-accent/40 bg-panel"
      } ${fullHeight ? "" : "min-h-[280px] shrink-0"}`}
    >
      {!floating && (
        <div className="shrink-0 border-b border-accent/30 bg-accent/5 px-4 py-3">
          <h2 className="font-mono text-sm font-semibold text-accent">Follow-up chat</h2>
          <p className="mt-0.5 text-xs text-muted">
            Ask about the diagnosis, Helm changes, or commands
          </p>
        </div>
      )}

      <div className={`min-h-0 flex-1 overflow-y-auto space-y-3 ${floating ? "px-3 py-2" : "px-4 py-3"}`}>
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
            className={`rounded border px-3 py-2.5 ${
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
            {msg.role === "user" ? (
              <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
            ) : (
              <ChatMessageBody content={msg.content} />
            )}
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

      <div className={`shrink-0 space-y-2 border-t border-border bg-void/40 ${floating ? "p-3" : "p-4"}`}>
        {lastAssistant && onSaveResolution && (
          <button
            type="button"
            onClick={saveLastReplyAsResolution}
            disabled={savingResolution}
            className="w-full border border-border py-2 font-mono text-[11px] text-neutral-400 transition-colors hover:border-accent/50 hover:text-accent disabled:opacity-40"
          >
            {savingResolution ? "Saving resolution..." : "Save last reply as resolution"}
          </button>
        )}
        <textarea
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
          rows={floating ? 2 : 3}
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
