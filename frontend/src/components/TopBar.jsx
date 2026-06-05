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
  const docsHref = API_BASE ? `${API_BASE}/docs` : "/docs"

  return (
    <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border bg-panel/90 px-3 py-2 backdrop-blur-sm">
      <div className="flex min-w-0 items-center gap-3">
        <div className="shrink-0">
          <h1 className="font-mono text-sm font-semibold text-accent">DebugPilot</h1>
          <p className="hidden font-mono text-[10px] text-muted sm:block">K8s · TF · CI · Docker</p>
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
              className={`flex items-center gap-1.5 border px-2.5 py-1.5 font-mono text-xs transition-colors ${
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
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {loading && (
          <span className="hidden animate-pulse font-mono text-xs text-info sm:inline">
            analyzing...
          </span>
        )}
        <a
          href={docsHref}
          target="_blank"
          rel="noreferrer"
          className="hidden font-mono text-[10px] text-accent hover:underline lg:inline"
        >
          API docs
        </a>
        <div className="hidden items-center gap-2 sm:flex">
          {user?.avatar_url && (
            <img src={user.avatar_url} alt="" className="h-6 w-6 border border-border" />
          )}
          <span className="max-w-[120px] truncate font-mono text-xs text-neutral-200">{sessionLabel}</span>
        </div>
        {authEnabled && user && (
          <button
            type="button"
            onClick={onLogout}
            className="border border-border px-2 py-1 font-mono text-[10px] text-neutral-400 hover:text-accent"
          >
            sign out
          </button>
        )}
        {authEnabled && !user && (
          <a
            href={loginUrl}
            className="border border-accent px-2 py-1 font-mono text-[10px] text-accent hover:bg-accent/10"
          >
            sign in
          </a>
        )}
        <div className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 ${apiOnline ? "bg-accent shadow-[0_0_8px_#22c55e]" : "bg-danger"}`}
          />
          <span className="font-mono text-[10px] text-muted">
            {apiOnline ? "online" : "offline"}
          </span>
        </div>
      </div>
    </header>
  )
}
