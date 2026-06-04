import { SAMPLE_PRESETS } from "../data/samples"

const SOURCE_OPTIONS = [
  { value: "", label: "Auto-detect" },
  { value: "kubernetes", label: "Kubernetes" },
  { value: "terraform", label: "Terraform" },
  { value: "github_actions", label: "GitHub Actions" },
  { value: "docker", label: "Docker" },
  { value: "app", label: "Application" },
]

function confidenceBadge(level) {
  if (level === "high") return "border-accent/40 bg-accent/10 text-accent"
  if (level === "medium") return "border-warn/40 bg-warn/10 text-warn"
  return "border-danger/40 bg-danger/10 text-danger"
}

async function copyText(text) {
  await navigator.clipboard.writeText(text)
}

export default function AnalyzePanel({
  logText,
  setLogText,
  sourceHint,
  setSourceHint,
  loading,
  uploading,
  uploadFilename,
  error,
  result,
  onAnalyze,
  onLoadPreset,
  onUploadFile,
}) {
  const lineCount = logText ? logText.split("\n").length : 1

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {/* Input */}
      <section className="border border-border bg-panel">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="font-mono text-sm font-semibold">Error log input</h2>
            <p className="text-xs text-muted">Paste or upload kubectl, Terraform, CI, or stack trace output</p>
          </div>
          <span className="font-mono text-[10px] text-muted">{lineCount} lines</span>
        </div>

        <div className="border-b border-border px-4 py-3">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted">Quick samples</p>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => onLoadPreset(preset)}
                className="border border-border bg-void px-2.5 py-1 font-mono text-[11px] text-neutral-300 transition-colors hover:border-accent/50 hover:text-accent"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <div className="px-4 py-3">
          <label htmlFor="source" className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-muted">
            Source hint
          </label>
          <select
            id="source"
            value={sourceHint}
            onChange={(e) => setSourceHint(e.target.value)}
            className="mb-3 w-full border border-border bg-void px-3 py-2 font-mono text-sm text-neutral-200 outline-none focus:border-accent"
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value || "auto"} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <div className="mb-3 flex flex-wrap items-center gap-2">
            <label className="cursor-pointer border border-border bg-void px-3 py-2 font-mono text-[11px] text-neutral-300 transition-colors hover:border-accent/50 hover:text-accent">
              {uploading ? "Uploading..." : "Upload .log / .txt"}
              <input
                type="file"
                accept=".log,.txt,.json,.out,.err,text/plain"
                className="hidden"
                disabled={uploading || loading}
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) onUploadFile(file)
                  e.target.value = ""
                }}
              />
            </label>
            {uploadFilename && (
              <span className="border border-info/30 bg-info/10 px-2 py-1 font-mono text-[10px] text-info">
                {uploadFilename}
              </span>
            )}
          </div>

          <div className="relative">
            <div className="absolute left-0 top-0 bottom-0 w-10 border-r border-border bg-black/40 pt-3 text-right font-mono text-[10px] leading-5 text-neutral-600 select-none">
              {Array.from({ length: Math.min(lineCount, 24) }, (_, i) => (
                <div key={i} className="pr-2">{i + 1}</div>
              ))}
            </div>
            <textarea
              value={logText}
              onChange={(e) => setLogText(e.target.value)}
              spellCheck={false}
              placeholder="$ kubectl describe pod api-xyz..."
              className="min-h-[340px] w-full resize-y border border-border bg-black py-3 pl-12 pr-4 font-mono text-[13px] leading-5 text-neutral-200 outline-none focus:border-accent"
            />
          </div>

          <button
            type="button"
            onClick={onAnalyze}
            disabled={loading || !logText.trim()}
            className="mt-3 w-full border border-accent bg-accent/15 py-3 font-mono text-sm font-semibold text-accent transition-colors hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Running diagnosis..." : "▸ Analyze incident"}
          </button>

          {error && (
            <div className="mt-3 border border-danger/40 bg-danger/10 px-3 py-2 font-mono text-xs text-red-300">
              {error}
            </div>
          )}
        </div>
      </section>

      {/* Output */}
      <section className="border border-border bg-panel">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="font-mono text-sm font-semibold">Diagnosis output</h2>
            <p className="text-xs text-muted">Structured root cause, commands, and fix</p>
          </div>
          {result && (
            <div className="flex flex-wrap items-center justify-end gap-2">
              {typeof result.cached === "boolean" && (
                <span
                  className={`border px-2 py-0.5 font-mono text-[10px] uppercase ${
                    result.cached
                      ? "border-info/40 bg-info/10 text-info"
                      : "border-accent/40 bg-accent/10 text-accent"
                  }`}
                >
                  {result.cached ? "Redis cache" : "Claude"}
                  {typeof result.duration_ms === "number" ? ` · ${result.duration_ms}ms` : ""}
                </span>
              )}
              <span className={`border px-2 py-0.5 font-mono text-[10px] uppercase ${confidenceBadge(result.confidence)}`}>
                {result.confidence}
              </span>
            </div>
          )}
        </div>

        {!result && (
          <div className="flex min-h-[420px] flex-col items-center justify-center px-6 text-center">
            <p className="font-mono text-4xl text-neutral-700">⌬</p>
            <p className="mt-3 font-mono text-sm text-neutral-400">No diagnosis yet</p>
            <p className="mt-1 max-w-xs text-xs text-muted">
              Paste a log or load a sample, then run analysis
            </p>
          </div>
        )}

        {result && (
          <div className="max-h-[520px] overflow-y-auto p-4">
            <div className="mb-3 inline-block border border-border bg-void px-2 py-1 font-mono text-[11px] uppercase text-info">
              {result.category}
            </div>

            <DiagnosisBlock title="Symptom" content={result.symptom} />
            <DiagnosisBlock title="What failed" content={result.what_failed} />
            <DiagnosisBlock title="Root cause" content={result.root_cause} highlight />
            <DiagnosisBlock title="Likely fix" content={result.likely_fix} highlight />

            {result.similar_incidents?.length > 0 && (
              <div className="mb-4 border border-border bg-void p-3">
                <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted">Matched playbooks</p>
                <div className="flex flex-wrap gap-2">
                  {result.similar_incidents.map((name) => (
                    <span key={name} className="border border-border px-2 py-0.5 font-mono text-[11px] text-neutral-300">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="mb-4 border border-border bg-void p-3">
              <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted">Debug commands</p>
              <ul className="space-y-2">
                {result.debug_commands.map((cmd) => (
                  <li key={cmd} className="flex items-start gap-2 border border-border bg-black p-2">
                    <code className="flex-1 break-all font-mono text-[12px] text-accent">{cmd}</code>
                    <button
                      type="button"
                      onClick={() => copyText(cmd)}
                      className="shrink-0 border border-border px-2 py-0.5 font-mono text-[10px] text-neutral-400 hover:text-accent"
                    >
                      copy
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {result.prevention?.length > 0 && (
              <ListBlock title="Prevention" items={result.prevention} />
            )}

            {result.warnings?.length > 0 && (
              <ListBlock title="Warnings" items={result.warnings} warn />
            )}
          </div>
        )}
      </section>
    </div>
  )
}

function DiagnosisBlock({ title, content, highlight }) {
  return (
    <div className={`mb-3 border p-3 ${highlight ? "border-accent/30 bg-accent/5" : "border-border bg-void"}`}>
      <p className="font-mono text-[10px] uppercase tracking-wider text-muted">{title}</p>
      <p className="mt-1 text-sm leading-relaxed text-neutral-200">{content}</p>
    </div>
  )
}

function ListBlock({ title, items, warn }) {
  return (
    <div className={`mb-4 border p-3 ${warn ? "border-warn/30 bg-warn/5" : "border-border bg-void"}`}>
      <p className="font-mono text-[10px] uppercase tracking-wider text-muted">{title}</p>
      <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-neutral-300">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  )
}
