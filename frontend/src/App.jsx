import { useCallback, useEffect, useState } from "react"
import axios from "axios"
import { API_BASE } from "./api"
import AnalyzePanel from "./components/AnalyzePanel"
import HistoryPanel from "./components/HistoryPanel"
import KpiCards from "./components/KpiCards"
import Sidebar from "./components/Sidebar"
import TopBar from "./components/TopBar"

export default function App() {
  const [view, setView] = useState("analyze")
  const [logText, setLogText] = useState("")
  const [sourceHint, setSourceHint] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [apiOnline, setApiOnline] = useState(false)

  const loadHistory = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/incidents`)
      setHistory(res.data)
    } catch {
      setHistory([])
    }
  }, [])

  const checkHealth = useCallback(async () => {
    try {
      await axios.get(`${API_BASE}/health`, { timeout: 3000 })
      setApiOnline(true)
    } catch {
      setApiOnline(false)
    }
  }, [])

  useEffect(() => {
    loadHistory()
    checkHealth()
    const interval = setInterval(checkHealth, 15000)
    return () => clearInterval(interval)
  }, [loadHistory, checkHealth])

  const analyze = async () => {
    if (!logText.trim()) return
    setLoading(true)
    setError("")
    try {
      const res = await axios.post(`${API_BASE}/analyze`, {
        log_text: logText,
        source_hint: sourceHint || null,
        save: true,
      })
      setResult(res.data)
      setView("analyze")
      loadHistory()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Analysis failed")
    } finally {
      setLoading(false)
    }
  }

  const loadIncident = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/incidents/${id}`)
      setResult(res.data)
      setView("analyze")
      setError("")
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  const loadPreset = (preset) => {
    setLogText(preset.log)
    setSourceHint(preset.source)
    setError("")
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar active={view} onNavigate={setView} historyCount={history.length} />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar apiOnline={apiOnline} loading={loading} />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="mb-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">infrastructure debugger</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-neutral-100">
              {view === "analyze" ? "Analyze incident" : "Incident history"}
            </h2>
            <p className="mt-1 text-sm text-muted">
              Paste logs from Kubernetes, Terraform, GitHub Actions, or Docker — get root cause and fix commands.
            </p>
          </div>

          <div className="mb-6">
            <KpiCards history={history} result={result} />
          </div>

          {view === "analyze" ? (
            <AnalyzePanel
              logText={logText}
              setLogText={setLogText}
              sourceHint={sourceHint}
              setSourceHint={setSourceHint}
              loading={loading}
              error={error}
              result={result}
              onAnalyze={analyze}
              onLoadPreset={loadPreset}
            />
          ) : (
            <HistoryPanel
              history={history}
              onSelect={loadIncident}
              onRefresh={loadHistory}
            />
          )}
        </main>
      </div>
    </div>
  )
}
