export default function TopBar({ apiOnline, loading }) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-panel/80 px-6 py-3 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <span className="font-mono text-xs text-muted">session</span>
        <span className="font-mono text-sm text-neutral-200">debug@local</span>
      </div>
      <div className="flex items-center gap-4">
        {loading && (
          <span className="animate-pulse font-mono text-xs text-info">analyzing log...</span>
        )}
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 ${apiOnline ? "bg-accent shadow-[0_0_8px_#22c55e]" : "bg-danger"}`}
          />
          <span className="font-mono text-xs text-muted">
            api {apiOnline ? "online" : "offline"}
          </span>
        </div>
      </div>
    </header>
  )
}
