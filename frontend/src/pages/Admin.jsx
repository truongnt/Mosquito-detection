import React, { useEffect, useMemo, useState } from "react"
import { adminHeaders, apiBase } from "../api.js"

function useInterval(callback, delay) {
  useEffect(() => {
    if (delay == null) return
    const id = setInterval(callback, delay)
    return () => clearInterval(id)
  }, [callback, delay])
}

export default function Admin() {
  const [tab, setTab] = useState("training")
  const [token, setToken] = useState(localStorage.getItem("ADMIN_TOKEN") || "")
  const [authOk, setAuthOk] = useState(false)
  const [authErr, setAuthErr] = useState("")

  const api = useMemo(() => apiBase(), [])

  async function checkAuth() {
    setAuthErr("")
    try {
      const resp = await fetch(`${api}/reports/health`, { headers: { ...adminHeaders() } })
      setAuthOk(resp.ok || resp.status === 200)
    } catch (e) {
      setAuthOk(false)
      setAuthErr(String(e?.message || e))
    }
  }

  useEffect(() => {
    checkAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function saveToken() {
    localStorage.setItem("ADMIN_TOKEN", token)
    checkAuth()
  }

  return (
    <div className="card">
      <h2>Quản trị</h2>
      <div className="row" style={{ alignItems: "center" }}>
        <input
          className="input"
          style={{ minWidth: 320 }}
          placeholder="ADMIN_TOKEN (Bearer)"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button className="btn primary" onClick={saveToken}>
          Lưu token
        </button>
        <span className="muted">{authOk ? "Auth: OK" : "Auth: chưa kiểm tra/không hợp lệ"}</span>
      </div>
      {authErr ? <p style={{ color: "#dc2626" }}>{authErr}</p> : null}

      <div className="row" style={{ marginTop: 12 }}>
        <button className={tab === "training" ? "btn primary" : "btn"} onClick={() => setTab("training")}>
          Training
        </button>
        <button className={tab === "logs" ? "btn primary" : "btn"} onClick={() => setTab("logs")}>
          Logs
        </button>
      </div>

      <div style={{ marginTop: 12 }}>
        {tab === "training" ? <TrainingTab api={api} /> : null}
        {tab === "logs" ? <LogsTab api={api} /> : null}
      </div>
    </div>
  )
}

function TrainingTab({ api }) {
  const [runs, setRuns] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [epochs, setEpochs] = useState(10)

  async function loadRuns() {
    try {
      const resp = await fetch(`${api}/admin/training/runs`, { headers: { ...adminHeaders() } })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setRuns(data)
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  useEffect(() => {
    loadRuns()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useInterval(() => loadRuns(), 2000)

  async function startRun() {
    setError("")
    setBusy(true)
    try {
      const resp = await fetch(`${api}/admin/training/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders() },
        body: JSON.stringify({ total_epochs: Number(epochs) || 10 }),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadRuns()
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="row" style={{ alignItems: "center" }}>
        <input
          className="input"
          type="number"
          min={1}
          max={500}
          value={epochs}
          onChange={(e) => setEpochs(e.target.value)}
        />
        <button className="btn primary" disabled={busy} onClick={startRun}>
          {busy ? "Đang tạo..." : "Start retrain"}
        </button>
        <button className="btn" onClick={loadRuns}>
          Refresh
        </button>
      </div>
      {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}

      <div style={{ marginTop: 12 }}>
        {runs.length === 0 ? <p className="muted">Chưa có training run.</p> : null}
        {runs.map((r) => (
          <div key={r.id} className="card" style={{ marginBottom: 10 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{r.id}</div>
                <div className="muted">
                  {r.status} — epoch {r.current_epoch}/{r.total_epochs}
                </div>
              </div>
              <div style={{ minWidth: 160, textAlign: "right" }}>{r.progress}%</div>
            </div>
            <div style={{ height: 10, background: "#e2e8f0", borderRadius: 999, overflow: "hidden", marginTop: 8 }}>
              <div style={{ width: `${r.progress}%`, height: "100%", background: "#2563eb" }} />
            </div>
            {r.error_message ? <p style={{ color: "#dc2626" }}>{r.error_message}</p> : null}
          </div>
        ))}
      </div>
    </div>
  )
}

function LogsTab({ api }) {
  const [service, setService] = useState("backend")
  const [tail, setTail] = useState(200)
  const [lines, setLines] = useState([])
  const [error, setError] = useState("")

  async function loadLogs() {
    setError("")
    try {
      const resp = await fetch(`${api}/admin/logs?service=${service}&tail=${tail}`, { headers: { ...adminHeaders() } })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setLines(data.lines || [])
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  useEffect(() => {
    loadLogs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service])

  useInterval(() => loadLogs(), 2000)

  return (
    <div>
      <div className="row" style={{ alignItems: "center" }}>
        <select className="select" value={service} onChange={(e) => setService(e.target.value)}>
          <option value="backend">backend</option>
          <option value="worker">worker</option>
        </select>
        <input className="input" type="number" min={1} max={5000} value={tail} onChange={(e) => setTail(e.target.value)} />
        <button className="btn" onClick={loadLogs}>
          Refresh
        </button>
      </div>
      {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}
      <pre style={{ marginTop: 12, maxHeight: 420 }}>{lines.join("\n")}</pre>
    </div>
  )
}
