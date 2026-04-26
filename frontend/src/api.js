export function apiBase() {
  const base = (import.meta.env.VITE_API_BASE || "").replace(/\/+$/, "")
  if (!base) return "/api"
  if (base.endsWith("/api")) return base
  return `${base}/api`
}

export async function apiFetch(path, options = {}) {
  const base = apiBase()
  const url = `${base}${path.startsWith("/") ? "" : "/"}${path}`
  const headers = { ...(options.headers || {}) }
  const resp = await fetch(url, { ...options, headers, credentials: "include" })
  return resp
}
