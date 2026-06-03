const NAV = [
  { id: "analyze", label: "Analyze", icon: "▸" },
  { id: "history", label: "History", icon: "◷" },
]

export default function Sidebar({ active, onNavigate, historyCount }) {
  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-panel">
      <div className="border-b border-border px-4 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">ops console</p>
        <h1 className="mt-1 font-mono text-lg font-semibold tracking-tight">DebugPilot</h1>
        <p className="mt-1 text-xs text-muted">AI incident debugger</p>
      </div>

      <nav className="flex-1 p-3">
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className={`mb-1 flex w-full items-center gap-2 border px-3 py-2.5 text-left font-mono text-sm transition-colors ${
              active === item.id
                ? "border-accent bg-accent/10 text-accent"
                : "border-transparent text-neutral-400 hover:border-border hover:bg-white/[0.03] hover:text-neutral-200"
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
            {item.id === "history" && historyCount > 0 && (
              <span className="ml-auto rounded-none bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-300">
                {historyCount}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="border-t border-border p-4 text-xs text-muted">
        <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Supported</p>
        <p className="mt-2 leading-relaxed">Kubernetes · Terraform · GitHub Actions · Docker</p>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-block font-mono text-accent hover:underline"
        >
          API docs →
        </a>
      </div>
    </aside>
  )
}
