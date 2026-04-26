import React, { useState } from "react"
import { useNavigate } from "react-router-dom"
import { apiFetch } from "../api.js"

export default function AdminLogin() {
  const navigate = useNavigate()
  const [username, setUsername] = useState("admin")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  async function onSubmit(e) {
    e.preventDefault()
    setError("")
    setBusy(true)
    try {
      const resp = await apiFetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `HTTP ${resp.status}`)
      }
      navigate("/admin")
    } catch (err) {
      setError(String(err?.message || err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="authWrap">
      <div className="authCard">
        <div className="authBrand">
          <div className="authLogo">MA</div>
          <div>
            <div className="authTitle">Admin</div>
            <div className="muted">Đăng nhập để quản trị training, log, cấu hình.</div>
          </div>
        </div>

        <form onSubmit={onSubmit} className="authForm">
          <label className="label">
            Username
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          </label>
          <label className="label">
            Password
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>

          {error ? <div className="alert danger">{error}</div> : null}

          <button className="btn primary" disabled={busy || !username || !password}>
            {busy ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  )
}

