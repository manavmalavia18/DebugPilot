export default function KpiCards({ history, result }) {
  const highConfidence = history.filter((h) => h.confidence === "high").length
  const categories = new Set(history.map((h) => h.category)).size

  const cards = [
    { label: "Saved analyses", value: history.length },
    { label: "High confidence", value: highConfidence },
    { label: "Categories seen", value: categories || "—" },
    {
      label: "Last result",
      value: result ? result.confidence : "—",
      accent: result?.confidence === "high",
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="border border-border bg-panel px-4 py-3"
        >
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted">{card.label}</p>
          <p
            className={`mt-1 font-mono text-2xl font-semibold ${
              card.accent ? "text-accent" : "text-neutral-100"
            }`}
          >
            {card.value}
          </p>
        </div>
      ))}
    </div>
  )
}
