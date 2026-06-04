import { API_BASE } from "../api"

export default function TopBar({
  apiOnline,
  loading,
  user,
  authEnabled,
  sessionLabel,
  onLogout,
}) {
  const loginUrl = `${API_BASE}/auth/github/login`

  return (
    <header className="flex items-center justify-between border-b border-border bg-panel/80 px-6 py-3 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        {user?.avatar_url && (
          <img
            src={user.avatar_url}
            alt=""
            className="h-7 w-7 border border-border"
          />
        )}
        <span className="font-mono text-xs text-muted">session</span>
        <span className="font-mono text-sm text-neutral-200">{sessionLabel}</span>
      </div>
      <div className="flex items-center gap-4">
        {loading && (
          <span className="animate-pulse font-mono text-xs text-info">analyzing log...</span>
        )}
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
