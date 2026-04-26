export function apiBase() {
  const base = (import.meta.env.VITE_API_BASE || "").replace(/\/+$/, "")
  if (!base) return "/api"
  if (base.endsWith("/api")) return base
  return `${base}/api`
}

export function adminHeaders() {
  const token = localStorage.getItem("ADMIN_TOKEN") || ""
  return token ? { Authorization: `Bearer ${token}` } : {}
}
