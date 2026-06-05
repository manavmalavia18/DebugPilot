import { useCallback, useEffect, useState } from "react"
import { api } from "./api"
import AnalyzePanel from "./components/AnalyzePanel"
import HistoryPanel from "./components/HistoryPanel"
import KpiCards from "./components/KpiCards"
import LoginGate from "./components/LoginGate"
import TopBar from "./components/TopBar"

const AUTH_ERRORS = {
  missing_code: "GitHub did not return an authorization code.",
}

export default function App() {
  const [view, setView] = useState("analyze")
  const [logText, setLogText] = useState("")
  const [sourceHint, setSourceHint] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState(null)
  const [incidentId, setIncidentId] = useState(null)
  const [history, setHistory] = useState([])
  const [apiOnline, setApiOnline] = useState(false)
  const [authEnabled, setAuthEnabled] = useState(false)
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [authError, setAuthError] = useState("")
  const [uploadId, setUploadId] = useState(null)
  const [uploadFilename, setUploadFilename] = useState("")
  const [uploading, setUploading] = useState(false)

  const loadAuth = useCallback(async ({ background = false } = {}) => {
    try {
      const configRes = await api.get("/auth/config")
      setAuthEnabled(Boolean(configRes.data.auth_enabled))
      const meRes = await api.get("/auth/me")
      setUser(meRes.data)
      return true
    } catch {
      setUser(null)
      return false
    } finally {
      if (!background) {
        setAuthLoading(false)
      }
    }
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get("/incidents")
      setHistory(res.data)
    } catch {
      setHistory([])
    }
  }, [])

  const checkHealth = useCallback(async () => {
    try {
      await api.get("/health", { timeout: 3000 })
      setApiOnline(true)
    } catch {
      setApiOnline(false)
    }
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const err = params.get("auth_error")
    if (err) {
      setAuthError(AUTH_ERRORS[err] || "Sign-in failed. Try again.")
      window.history.replaceState({}, "", window.location.pathname)
    }
    loadAuth()
    checkHealth()
    const interval = setInterval(checkHealth, 15000)
    return () => clearInterval(interval)
  }, [loadAuth, checkHealth])

  useEffect(() => {
    if (!authEnabled) return undefined

    const syncSession = () => {
      if (document.visibilityState === "visible") {
        loadAuth({ background: true })
      }
    }

    document.addEventListener("visibilitychange", syncSession)
    return () => document.removeEventListener("visibilitychange", syncSession)
  }, [authEnabled, loadAuth])

  useEffect(() => {
    if (user) {
      loadHistory()
    } else {
      setHistory([])
    }
  }, [user, loadHistory])

  const analyze = async () => {
    if (!logText.trim() && !uploadId) return
    setLoading(true)
    setError("")
    setIncidentId(null)
    try {
      const payload = {
        log_text: logText,
        source_hint: sourceHint || null,
        save: true,
      }
      if (uploadId) payload.upload_id = uploadId
      const res = await api.post("/analyze", payload)
      setResult(res.data)
      setIncidentId(res.data.incident_id ?? null)
      setView("analyze")
      loadHistory()
    } catch (err) {
      if (err.response?.status === 401) {
        setUser(null)
        setError("Your session expired. Sign in again to analyze logs.")
      } else {
        setError(err.response?.data?.detail || err.message || "Analysis failed")
      }
    } finally {
      setLoading(false)
    }
  }

  const loadIncident = async (id) => {
    try {
      const res = await api.get(`/incidents/${id}`)
      setResult({ ...res.data, cached: undefined, duration_ms: undefined })
      setIncidentId(id)
      setView("analyze")
      setError("")
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  const logout = async () => {
    try {
      await api.post("/auth/logout")
    } catch {
      /* ignore */
    }
    setUser(null)
    setResult(null)
    setIncidentId(null)
    setHistory([])
  }

  const loadPreset = (preset) => {
    setLogText(preset.log)
    setSourceHint(preset.source)
    setUploadId(null)
    setUploadFilename("")
    setError("")
  }

  const uploadLogFile = async (file) => {
    setUploading(true)
    setError("")
    const form = new FormData()
    form.append("file", file)
    try {
      if (authEnabled) {
        const sessionOk = await loadAuth({ background: true })
        if (!sessionOk) {
          setAuthError("Your session expired. Sign in again to upload logs.")
          return
        }
      }
      const res = await api.post("/uploads", form)
      setLogText(res.data.log_text)
      setUploadId(res.data.id)
      setUploadFilename(res.data.filename)
    } catch (err) {
      if (err.response?.status === 401) {
        setUser(null)
        setAuthError("Your session expired. Sign in again to upload logs.")
      } else {
        setError(err.response?.data?.detail || err.message || "Upload failed")
      }
    } finally {
      setUploading(false)
    }
  }

  const handleLogTextChange = (value) => {
    setLogText(value)
    if (uploadId) {
      setUploadId(null)
      setUploadFilename("")
    }
  }

  const needsLogin = authEnabled && !user
  const sessionLabel = user
    ? authEnabled
      ? `@${user.username}`
      : user.username
    : "guest"

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopBar
        apiOnline={apiOnline}
        loading={loading}
        user={user}
        authEnabled={authEnabled}
        sessionLabel={sessionLabel}
        activeView={view}
        historyCount={history.length}
        onNavigate={setView}
        onLogout={logout}
      />

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden px-3 py-2">
        {authLoading ? (
          <p className="font-mono text-sm text-muted">Checking session...</p>
        ) : needsLogin ? (
          <LoginGate authError={authError} />
        ) : (
          <>
            {view === "history" && (
              <div className="mb-2 shrink-0">
                <KpiCards history={history} result={result} />
              </div>
            )}

            <div className="min-h-0 flex-1 overflow-hidden">
              {view === "analyze" ? (
                <AnalyzePanel
                  logText={logText}
                  setLogText={handleLogTextChange}
                  sourceHint={sourceHint}
                  setSourceHint={setSourceHint}
                  loading={loading}
                  uploading={uploading}
                  uploadFilename={uploadFilename}
                  error={error}
                  result={result}
                  incidentId={incidentId}
                  onAnalyze={analyze}
                  onLoadPreset={loadPreset}
                  onUploadFile={uploadLogFile}
                  onLoadIncident={loadIncident}
                />
              ) : (
                <div className="h-full overflow-y-auto">
                  <HistoryPanel
                    history={history}
                    onSelect={loadIncident}
                    onRefresh={loadHistory}
                  />
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
