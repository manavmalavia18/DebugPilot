import axios from "axios"

// Production: UI is served from FastAPI — use same-origin relative paths ("").
// Local dev: set VITE_API_URL (see .env.development) or use Vite proxy (credentials).
export const API_BASE = import.meta.env.VITE_API_URL ?? ""

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})
