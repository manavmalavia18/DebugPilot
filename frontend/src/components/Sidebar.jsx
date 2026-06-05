import { API_BASE } from "../api"

const NAV = [
  { id: "analyze", label: "Analyze", icon: "▸" },
  { id: "history", label: "History", icon: "◷" },
]

export default function Sidebar({ active, onNavigate, historyCount }) {
  const docsHref = API_BASE ? `${API_BASE}/docs` : "/docs"

  return (
    <aside className="flex h-screen w-52 shrink-0 flex-col border-r border-border bg-panel">
      <div className="shrink-0 border-b border-border px-3 py-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">ops console</p>
        <h1 className="mt-0.5 font-mono text-base font-semibold tracking-tight">DebugPilot</h1>
        <p className="text-[11px] text-muted">AI incident debugger</p>
      </div>

      <nav className="shrink-0 space-y-1 p-2">
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className={`flex w-full items-center gap-2 border px-3 py-2 text-left font-mono text-sm transition-colors ${
              active === item.id
                ? "border-accent bg-accent/10 text-accent"
                : "border-transparent text-neutral-400 hover:border-border hover:bg-white/[0.03] hover:text-neutral-200"
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
            {item.id === "history" && historyCount > 0 && (
              <span className="ml-auto bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-300">
                {historyCount}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="mt-auto shrink-0 border-t border-border p-3 text-[11px] text-muted">
        <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Supported</p>
        <p className="mt-1 leading-snug">K8s · TF · CI · Docker</p>
        <a
          href={docsHref}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block font-mono text-[11px] text-accent hover:underline"
        >
          API docs →
        </a>
      </div>
    </aside>
  )
}
