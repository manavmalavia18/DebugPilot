import { API_BASE } from "../api"

export default function LoginGate({ authError }) {
  const loginUrl = `${API_BASE}/auth/github/login`

  return (
    <div className="mx-auto max-w-lg border border-border bg-panel p-8 text-center">
      <p className="font-mono text-4xl text-neutral-600">◈</p>
      <h2 className="mt-4 text-lg font-semibold text-neutral-100">Sign in to analyze</h2>
      <p className="mt-2 text-sm text-muted">
        DebugPilot uses GitHub sign-in so only authenticated users can run Claude analysis
        and save incident history.
      </p>
      {authError && (
        <p className="mt-4 border border-danger/40 bg-danger/10 px-3 py-2 font-mono text-xs text-red-300">
          {authError}
        </p>
      )}
      <a
        href={loginUrl}
        className="mt-6 inline-block border border-accent bg-accent/15 px-6 py-3 font-mono text-sm font-semibold text-accent transition-colors hover:bg-accent/25"
      >
        Sign in with GitHub
      </a>
    </div>
  )
}
