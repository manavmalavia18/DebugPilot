import { API_BASE } from "../api"

function sessionInitial(sessionLabel, user) {
  if (user?.username) return user.username[0].toUpperCase()
  if (sessionLabel.startsWith("@")) return sessionLabel[1]?.toUpperCase() || "?"
  return sessionLabel[0]?.toUpperCase() || "?"
}

function sessionMode(authEnabled, user) {
  if (authEnabled && user) return "github auth"
  if (authEnabled) return "awaiting sign-in"
  return "local sandbox"
}

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
  const initial = sessionInitial(sessionLabel, user)

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

        <div
          className={`relative hidden overflow-hidden border bg-void/60 sm:block ${
            apiOnline ? "border-accent/30" : "border-danger/40"
          }`}
        >
          <div
            className={`absolute inset-y-0 left-0 w-0.5 ${
              apiOnline ? "bg-accent shadow-[0_0_10px_#22c55e]" : "bg-danger"
            }`}
          />

          <div className="flex items-center gap-3 px-3 py-2 pl-3.5">
            {user?.avatar_url ? (
              <div className="relative shrink-0">
                <img
                  src={user.avatar_url}
                  alt=""
                  className={`h-9 w-9 border-2 ${
                    apiOnline ? "border-accent/40" : "border-danger/40"
                  }`}
                />
                <span
                  className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 border-2 border-void ${
                    apiOnline ? "bg-accent shadow-[0_0_6px_#22c55e]" : "bg-danger"
                  }`}
                />
              </div>
            ) : (
              <div
                className={`relative flex h-9 w-9 shrink-0 items-center justify-center border-2 font-mono text-sm font-bold ${
                  apiOnline
                    ? "border-accent/40 bg-accent/10 text-accent"
                    : "border-danger/40 bg-danger/10 text-danger"
                }`}
              >
                {initial}
                <span
                  className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 border-2 border-void ${
                    apiOnline ? "bg-accent" : "bg-danger"
                  }`}
                />
              </div>
            )}

            <div className="min-w-0 leading-tight">
              <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted">session</p>
              <p className="truncate font-mono text-sm font-medium text-neutral-100">{sessionLabel}</p>
              <p className="font-mono text-[10px] text-muted">
                {sessionMode(authEnabled, user)}
                <span className="mx-1.5 text-border">·</span>
                <span className={apiOnline ? "text-accent" : "text-danger"}>
                  {apiOnline ? "api live" : "api down"}
                </span>
              </p>
            </div>

            {authEnabled && user && (
              <button
                type="button"
                onClick={onLogout}
                className="ml-1 shrink-0 border border-border px-2 py-1 font-mono text-[10px] text-neutral-400 transition-colors hover:border-accent/50 hover:text-accent"
              >
                exit
              </button>
            )}
            {authEnabled && !user && (
              <a
                href={loginUrl}
                className="ml-1 shrink-0 border border-accent bg-accent/10 px-2 py-1 font-mono text-[10px] text-accent transition-colors hover:bg-accent/20"
              >
                sign in
              </a>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
