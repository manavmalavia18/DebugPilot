// Production: UI is served from FastAPI — use same-origin relative paths ("").
// Local dev: set VITE_API_URL (see .env.development or scripts/dev.sh).
export const API_BASE = import.meta.env.VITE_API_URL ?? ""
