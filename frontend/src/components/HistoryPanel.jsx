function confidenceDot(level) {
  if (level === "high") return "bg-accent"
  if (level === "medium") return "bg-warn"
  return "bg-danger"
}

export default function HistoryPanel({ history, onSelect, onRefresh }) {
  return (
    <section className="border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="font-mono text-sm font-semibold">Incident history</h2>
          <p className="text-xs text-muted">Previously saved analyses from this session</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="border border-border px-3 py-1.5 font-mono text-[11px] text-neutral-400 hover:border-accent/50 hover:text-accent"
        >
          refresh
        </button>
      </div>

      {history.length === 0 ? (
        <p className="px-4 py-12 text-center text-sm text-muted">No saved analyses yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-sm">
            <thead className="border-b border-border text-[10px] uppercase tracking-wider text-muted">
              <tr>
                <th className="px-4 py-3 font-normal">When</th>
                <th className="px-4 py-3 font-normal">Category</th>
                <th className="px-4 py-3 font-normal">Symptom</th>
                <th className="px-4 py-3 font-normal">File</th>
                <th className="px-4 py-3 font-normal">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onSelect(item.id)}
                  className="cursor-pointer border-b border-border/60 transition-colors hover:bg-white/[0.03]"
                >
                  <td className="px-4 py-3 text-xs text-muted whitespace-nowrap">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs text-info">{item.category}</td>
                  <td className="max-w-md truncate px-4 py-3 text-neutral-200">{item.symptom}</td>
                  <td className="max-w-[140px] truncate px-4 py-3 text-xs text-muted">
                    {item.source_filename || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-2 text-xs capitalize text-neutral-400">
                      <span className={`h-1.5 w-1.5 ${confidenceDot(item.confidence)}`} />
                      {item.confidence}
                      {item.resolution && (
                        <span className="text-accent" title="Has confirmed fix">
                          ✓
                        </span>
                      )}
                      {item.feedback === "up" && (
                        <span className="text-accent" title="Marked helpful">
                          +
                        </span>
                      )}
                      {item.feedback === "down" && (
                        <span className="text-danger" title="Marked not helpful">
                          −
                        </span>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
