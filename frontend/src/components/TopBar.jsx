import { API_BASE } from "../api"

export default function TopBar({
  apiOnline,
  loading,
  user,
  authEnabled,
  sessionLabel,
  activeView,
  historyCount,
  onNavigate,
  onLogout,
}) {
  const loginUrl = `${API_BASE}/auth/github/login`

  return (
    <header className="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-4 border-b border-border bg-panel/90 px-4 py-3 backdrop-blur-sm">
      <div className="min-w-0 leading-tight">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">ops console</p>
        <h1 className="mt-0.5 font-mono text-2xl font-bold tracking-tight text-neutral-50 sm:text-3xl">
          DebugPilot
        </h1>
        <p className="mt-0.5 hidden text-[11px] text-muted sm:block">AI incident debugger</p>
      </div>

      <nav className="flex items-center gap-1">
        {[
          { id: "analyze", label: "Analyze", icon: "▸" },
          { id: "history", label: "History", icon: "◷" },
        ].map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className={`flex items-center gap-1.5 border px-3 py-2 font-mono text-sm transition-colors ${
              activeView === item.id
                ? "border-accent bg-accent/10 text-accent"
                : "border-transparent text-neutral-400 hover:border-border hover:text-neutral-200"
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
            {item.id === "history" && historyCount > 0 && (
              <span className="bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-300">
                {historyCount}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="flex min-w-0 items-center justify-end gap-3">
        {loading && (
          <span className="hidden animate-pulse font-mono text-xs text-info sm:inline">
            analyzing...
          </span>
        )}

        <div className="hidden items-center gap-2.5 sm:flex">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="h-8 w-8 border border-border" />
          ) : (
            <div className="flex h-8 w-8 items-center justify-center border border-border bg-neutral-900 font-mono text-xs text-neutral-400">
              {sessionLabel.replace("@", "").charAt(0).toUpperCase()}
            </div>
          )}

          <div className="min-w-0 font-mono leading-tight">
            <p className="truncate text-sm text-neutral-100">{sessionLabel}</p>
            <p className="flex items-center gap-1.5 text-[10px] text-muted">
              {authEnabled && user ? "GitHub" : authEnabled ? "Guest" : "Local"}
              <span className="text-border">·</span>
              <span className={`inline-flex items-center gap-1 ${apiOnline ? "text-accent" : "text-danger"}`}>
                <span
                  className={`h-1.5 w-1.5 ${apiOnline ? "bg-accent" : "bg-danger"}`}
                />
                {apiOnline ? "online" : "offline"}
              </span>
            </p>
          </div>

          {authEnabled && user && (
            <button
              type="button"
              onClick={onLogout}
              className="ml-1 border border-border px-2 py-1 font-mono text-[10px] text-neutral-400 hover:border-neutral-600 hover:text-neutral-200"
            >
              sign out
            </button>
          )}
          {authEnabled && !user && (
            <a
              href={loginUrl}
              className="ml-1 border border-accent px-2 py-1 font-mono text-[10px] text-accent hover:bg-accent/10"
            >
              sign in
            </a>
          )}
        </div>
      </div>
    </header>
  )
}
