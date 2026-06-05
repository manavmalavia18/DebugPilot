import { useEffect, useState } from "react"
import FollowUpChat from "./FollowUpChat"

export default function FloatingChatPanel({ incidentId }) {
  const [open, setOpen] = useState(false)
  const [lastIncidentId, setLastIncidentId] = useState(null)
  const [hasNewReply, setHasNewReply] = useState(false)

  useEffect(() => {
    if (!incidentId) {
      setOpen(false)
      setHasNewReply(false)
      setLastIncidentId(null)
      return
    }
    if (incidentId !== lastIncidentId) {
      setLastIncidentId(incidentId)
      setHasNewReply(true)
    }
  }, [incidentId, lastIncidentId])

  if (!incidentId) return null

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => {
          setOpen(true)
          setHasNewReply(false)
        }}
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2 border border-accent/60 bg-panel/95 px-4 py-3 font-mono text-sm text-accent shadow-[0_0_24px_rgba(34,197,94,0.25)] backdrop-blur-md transition-transform hover:scale-[1.02] hover:border-accent"
      >
        <span className="relative flex h-2 w-2">
          {hasNewReply && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
          )}
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent shadow-[0_0_8px_#22c55e]" />
        </span>
        Follow-up chat
      </button>
    )
  }

  return (
    <div
      className="fixed bottom-5 right-5 z-50 flex h-[min(520px,calc(100vh-7rem))] w-[min(400px,calc(100vw-1.5rem))] flex-col overflow-hidden border border-accent/40 bg-panel/95 shadow-[0_8px_40px_rgba(0,0,0,0.55),0_0_0_1px_rgba(34,197,94,0.15)] backdrop-blur-md animate-[chatSlideIn_0.28s_ease-out]"
      role="dialog"
      aria-label="Follow-up chat"
    >
      <div className="flex shrink-0 items-center justify-between border-b border-accent/30 bg-accent/5 px-3 py-2.5">
        <div>
          <h2 className="font-mono text-sm font-semibold text-accent">Follow-up chat</h2>
          <p className="text-[10px] text-muted">Ask about the diagnosis or commands</p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="border border-border px-2 py-1 font-mono text-[10px] text-neutral-400 transition-colors hover:border-accent/50 hover:text-accent"
          aria-label="Minimize chat"
        >
          minimize
        </button>
      </div>

      <div className="min-h-0 flex-1">
        <FollowUpChat incidentId={incidentId} fullHeight floating />
      </div>
    </div>
  )

}
