import { useState } from "react"
import axios from "axios"

const API = "http://localhost:8000"

export default function App() {
  const [jobs, setJobs] = useState([])
  const [cvText, setCvText] = useState("")
  const [loading, setLoading] = useState(false)
  const [matchLoading, setMatchLoading] = useState(false)
  const [coverLetter, setCoverLetter] = useState(null)
  const [coverLoading, setCoverLoading] = useState(null)
  const [search, setSearch] = useState("")
  const [activeTab, setActiveTab] = useState("jobs")

  const fetchJobs = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API}/jobs`, {
        params: search ? { title: search } : {}
      })
      setJobs(res.data.map(job => ({ ...job, score: null })))
    } catch (e) {
      alert("Error fetching jobs")
    }
    setLoading(false)
  }

  const matchJobs = async () => {
    if (!cvText.trim()) return alert("Paste your CV first")
    setMatchLoading(true)
    try {
      const res = await axios.post(`${API}/match`, {
        cv_text: cvText,
        limit: 10
      })
      setJobs(res.data.map(item => ({ ...item.job, score: item.score, reason: item.reason, missing: item.missing })))
      setActiveTab("jobs")
    } catch (e) {
      alert("Error matching jobs")
    }
    setMatchLoading(false)
  }

  const getCoverLetter = async (jobId) => {
    if (!cvText.trim()) return alert("Paste your CV first")
    setCoverLoading(jobId)
    try {
      const res = await axios.post(`${API}/cover-letter/${jobId}`, { cv_text: cvText })
      setCoverLetter({ text: res.data.cover_letter, job: res.data.job })
    } catch (e) {
      alert("Error generating cover letter")
    }
    setCoverLoading(null)
  }

  const scoreColor = (score) => {
    if (score >= 70) return "#22c55e"
    if (score >= 40) return "#f59e0b"
    return "#ef4444"
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px", fontFamily: "system-ui, sans-serif" }}>
      
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, margin: "0 0 4px" }}>JobRadar</h1>
        <p style={{ color: "#6b7280", margin: 0 }}>AI-powered job matching — paste your CV, get ranked results</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <button
          onClick={() => setActiveTab("jobs")}
          style={{ padding: "8px 16px", borderRadius: 8, border: "none", cursor: "pointer", background: activeTab === "jobs" ? "#111827" : "#f3f4f6", color: activeTab === "jobs" ? "#fff" : "#111827", fontWeight: 500 }}
        >
          Jobs
        </button>
        <button
          onClick={() => setActiveTab("cv")}
          style={{ padding: "8px 16px", borderRadius: 8, border: "none", cursor: "pointer", background: activeTab === "cv" ? "#111827" : "#f3f4f6", color: activeTab === "cv" ? "#fff" : "#111827", fontWeight: 500 }}
        >
          My CV
        </button>
      </div>

      {activeTab === "cv" && (
        <div>
          <p style={{ color: "#6b7280", marginBottom: 8, fontSize: 14 }}>Paste your CV text below. Claude will use it to score and rank jobs for you.</p>
          <textarea
            value={cvText}
            onChange={e => setCvText(e.target.value)}
            placeholder="Paste your CV here..."
            style={{ width: "100%", height: 300, padding: 12, borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 14, resize: "vertical", boxSizing: "border-box" }}
          />
          <button
            onClick={matchJobs}
            disabled={matchLoading}
            style={{ marginTop: 12, padding: "10px 20px", background: "#111827", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 500 }}
          >
            {matchLoading ? "Matching..." : "Match Jobs with AI"}
          </button>
        </div>
      )}

      {activeTab === "jobs" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by title..."
              style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 14 }}
              onKeyDown={e => e.key === "Enter" && fetchJobs()}
            />
            <button
              onClick={fetchJobs}
              disabled={loading}
              style={{ padding: "8px 16px", background: "#111827", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 500 }}
            >
              {loading ? "Loading..." : "Search"}
            </button>
          </div>

          {jobs.length === 0 && (
            <div style={{ textAlign: "center", padding: "48px 0", color: "#9ca3af" }}>
              <p>No jobs loaded yet.</p>
              <p style={{ fontSize: 14 }}>Hit Search to load jobs, or go to My CV tab to match with AI.</p>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {jobs.map(job => (
              <div key={job.id} style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 16, background: "#fff" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div>
                    <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 600 }}>{job.title}</h3>
                    <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>{job.company} · {job.location}</p>
                  </div>
                  {job.score !== null && (
                    <div style={{ textAlign: "center", minWidth: 56 }}>
                      <div style={{ fontSize: 22, fontWeight: 700, color: scoreColor(job.score) }}>{job.score}</div>
                      <div style={{ fontSize: 11, color: "#9ca3af" }}>match</div>
                    </div>
                  )}
                </div>

                {job.reason && (
                  <p style={{ fontSize: 13, color: "#374151", margin: "8px 0 4px", background: "#f9fafb", padding: "8px 10px", borderRadius: 6 }}>
                    {job.reason}
                  </p>
                )}
                {job.missing && (
                  <p style={{ fontSize: 12, color: "#dc2626", margin: "4px 0 8px" }}>
                    Missing: {job.missing}
                  </p>
                )}

                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <a href={job.url} target="_blank" rel="noreferrer"
                    style={{ fontSize: 13, color: "#2563eb", textDecoration: "none" }}>
                    View job →
                  </a>
                  <button
                    onClick={() => getCoverLetter(job.id)}
                    disabled={coverLoading === job.id}
                    style={{ fontSize: 13, padding: "4px 10px", background: "#f3f4f6", border: "none", borderRadius: 6, cursor: "pointer" }}
                  >
                    {coverLoading === job.id ? "Generating..." : "Cover letter"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {coverLetter && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50, padding: 16 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: 24, maxWidth: 640, width: "100%", maxHeight: "80vh", overflow: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Cover letter — {coverLetter.job.title} at {coverLetter.job.company}</h3>
              <button onClick={() => setCoverLetter(null)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#6b7280" }}>×</button>
            </div>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6, margin: 0, color: "#374151" }}>{coverLetter.text}</pre>
            <button
              onClick={() => { navigator.clipboard.writeText(coverLetter.text); alert("Copied!") }}
              style={{ marginTop: 16, padding: "8px 16px", background: "#111827", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 500 }}
            >
              Copy to clipboard
            </button>
          </div>
        </div>
      )}
    </div>
  )
}