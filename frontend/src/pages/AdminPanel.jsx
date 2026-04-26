import React, { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { apiFetch } from "../api.js"

function useInterval(callback, delay) {
  useEffect(() => {
    if (delay == null) return
    const id = setInterval(callback, delay)
    return () => clearInterval(id)
  }, [callback, delay])
}

function statusColor(status) {
  if (status === "succeeded") return "success"
  if (status === "failed") return "danger"
  if (status === "running") return "info"
  return "muted"
}

function Sparkline({ values = [], width = 140, height = 36 }) {
  if (!values.length) return <div className="muted">—</div>
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = Math.max(1e-6, max - min)
  const points = values
    .map((v, i) => {
      const x = (i / Math.max(1, values.length - 1)) * (width - 2) + 1
      const y = height - 1 - ((v - min) / range) * (height - 2)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(" ")
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="spark">
      <polyline fill="none" stroke="currentColor" strokeWidth="2" points={points} />
    </svg>
  )
}

function ProgressRing({ value }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0))
  const r = 14
  const c = 2 * Math.PI * r
  const offset = c - (v / 100) * c
  return (
    <svg width="36" height="36" viewBox="0 0 36 36">
      <circle cx="18" cy="18" r={r} fill="none" stroke="#e2e8f0" strokeWidth="4" />
      <circle
        cx="18"
        cy="18"
        r={r}
        fill="none"
        stroke="#2563eb"
        strokeWidth="4"
        strokeDasharray={`${c} ${c}`}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 18 18)"
      />
      <text x="18" y="21" textAnchor="middle" fontSize="9" fill="#0f172a">
        {Math.round(v)}%
      </text>
    </svg>
  )
}

export default function AdminPanel() {
  const navigate = useNavigate()
  const [me, setMe] = useState(null)
  const [tab, setTab] = useState("overview")
  const [error, setError] = useState("")

  async function loadMe() {
    const resp = await apiFetch("/auth/me")
    if (resp.status === 401) {
      navigate("/admin/login")
      return
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    setMe(data)
  }

  useEffect(() => {
    loadMe().catch((e) => setError(String(e?.message || e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function logout() {
    await apiFetch("/auth/logout", { method: "POST" })
    navigate("/admin/login")
  }

  if (!me) {
    return (
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Quản trị</h2>
            <div className="muted">Đang kiểm tra đăng nhập...</div>
          </div>
        </div>
        {error ? <div className="alert danger">{error}</div> : null}
      </div>
    )
  }

  return (
    <div className="adminShell">
      <div className="adminTop">
        <div>
          <div className="adminH1">Dashboard</div>
          <div className="muted">Xin chào {me.username}</div>
        </div>
        <div className="row" style={{ alignItems: "center" }}>
          <button className="btn" onClick={() => navigate("/")}>
            Về trang nhận dạng
          </button>
          <button className="btn danger" onClick={logout}>
            Đăng xuất
          </button>
        </div>
      </div>

      <div className="adminBody">
        <div className="adminNav">
          <button className={tab === "overview" ? "navBtn active" : "navBtn"} onClick={() => setTab("overview")}>
            Tổng quan
          </button>
          <button className={tab === "data" ? "navBtn active" : "navBtn"} onClick={() => setTab("data")}>
            Dữ liệu
          </button>
          <button className={tab === "training" ? "navBtn active" : "navBtn"} onClick={() => setTab("training")}>
            Training
          </button>
          <button className={tab === "config" ? "navBtn active" : "navBtn"} onClick={() => setTab("config")}>
            Cấu hình
          </button>
          <button className={tab === "logs" ? "navBtn active" : "navBtn"} onClick={() => setTab("logs")}>
            Logs
          </button>
        </div>

        <div className="adminMain">
          {tab === "overview" ? <Overview /> : null}
          {tab === "data" ? <Data /> : null}
          {tab === "training" ? <Training /> : null}
          {tab === "config" ? <Config /> : null}
          {tab === "logs" ? <Logs /> : null}
        </div>
      </div>
    </div>
  )
}

function Overview() {
  const [runs, setRuns] = useState([])
  const [err, setErr] = useState("")

  async function load() {
    setErr("")
    try {
      const resp = await apiFetch("/admin/training/runs")
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setRuns(data)
    } catch (e) {
      setErr(String(e?.message || e))
    }
  }

  useEffect(() => {
    load()
  }, [])

  useInterval(() => load(), 3000)

  const latest = runs[0]
  const accuracyHistory = latest?.metrics_json?.history?.val_accuracy || []

  return (
    <div className="grid2">
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div className="kpiLabel">Training gần nhất</div>
            <div className="kpiValue">{latest ? latest.id.slice(0, 8) : "—"}</div>
            <div className={`badge ${statusColor(latest?.status)}`}>{latest ? latest.status : "no runs"}</div>
          </div>
          <ProgressRing value={latest?.progress || 0} />
        </div>
      </div>

      <div className="card">
        <div className="kpiLabel">Val Accuracy (sparkline)</div>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div className="kpiValue">{latest?.metrics_json?.val_accuracy ?? "—"}</div>
          <Sparkline values={accuracyHistory} />
        </div>
        <div className="muted">Tự động cập nhật mỗi 3s</div>
      </div>

      <div className="card" style={{ gridColumn: "1 / -1" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Runs</h3>
          <button className="btn" onClick={load}>
            Refresh
          </button>
        </div>
        {err ? <div className="alert danger">{err}</div> : null}
        <div className="table">
          <div className="tr th">
            <div>ID</div>
            <div>Trạng thái</div>
            <div>Epoch</div>
            <div>Progress</div>
            <div>Val acc</div>
          </div>
          {runs.slice(0, 10).map((r) => (
            <div key={r.id} className="tr">
              <div className="mono">{r.id.slice(0, 10)}</div>
              <div>
                <span className={`badge ${statusColor(r.status)}`}>{r.status}</span>
              </div>
              <div>
                {r.current_epoch}/{r.total_epochs}
              </div>
              <div>
                <div className="bar">
                  <div className="barFill" style={{ width: `${r.progress}%` }} />
                </div>
                <div className="muted">{r.progress}%</div>
              </div>
              <div className="mono">{r.metrics_json?.val_accuracy ?? "—"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Training() {
  const [runs, setRuns] = useState([])
  const [selected, setSelected] = useState(null)
  const [epochs, setEpochs] = useState(10)
  const [lr, setLr] = useState(0.001)
  const [bs, setBs] = useState(32)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")
  const [events, setEvents] = useState([])

  async function loadRuns() {
    const resp = await apiFetch("/admin/training/runs")
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    setRuns(data)
    if (!selected && data[0]) setSelected(data[0].id)
  }

  async function loadEvents(runId) {
    if (!runId) return
    const resp = await apiFetch(`/admin/training/runs/${runId}/events?limit=200`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    setEvents(data)
  }

  async function refresh() {
    setErr("")
    try {
      await loadRuns()
    } catch (e) {
      setErr(String(e?.message || e))
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  useInterval(() => refresh(), 2000)
  useInterval(() => loadEvents(selected).catch(() => {}), 2000)

  const current = useMemo(() => runs.find((r) => r.id === selected) || null, [runs, selected])
  const accHistory = current?.metrics_json?.history?.val_accuracy || []
  const lossHistory = current?.metrics_json?.history?.val_loss || []

  async function startRun() {
    setErr("")
    setBusy(true)
    try {
      const resp = await apiFetch("/admin/training/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          total_epochs: Number(epochs) || 10,
          learning_rate: Number(lr) || 0.001,
          batch_size: Number(bs) || 32,
          note: note || null,
        }),
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `HTTP ${resp.status}`)
      }
      await refresh()
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid2">
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Tạo retrain</h3>
        <div className="formGrid">
          <label className="label">
            Epochs
            <input className="input" type="number" min={1} max={500} value={epochs} onChange={(e) => setEpochs(e.target.value)} />
          </label>
          <label className="label">
            Learning rate
            <input className="input" type="number" step="0.0001" value={lr} onChange={(e) => setLr(e.target.value)} />
          </label>
          <label className="label">
            Batch size
            <input className="input" type="number" min={1} max={4096} value={bs} onChange={(e) => setBs(e.target.value)} />
          </label>
          <label className="label" style={{ gridColumn: "1 / -1" }}>
            Ghi chú
            <textarea className="input" rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
        </div>

        {err ? <div className="alert danger">{err}</div> : null}
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <button className="btn primary" disabled={busy} onClick={startRun}>
            {busy ? "Đang tạo..." : "Start retrain"}
          </button>
          <button className="btn" onClick={refresh}>
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Chi tiết run</h3>
        <label className="label">
          Chọn run
          <select className="select" value={selected || ""} onChange={(e) => setSelected(e.target.value)}>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id}
              </option>
            ))}
          </select>
        </label>

        {current ? (
          <>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <span className={`badge ${statusColor(current.status)}`}>{current.status}</span>
              <ProgressRing value={current.progress} />
            </div>
            <div className="muted">
              epoch {current.current_epoch}/{current.total_epochs}
            </div>
            <div className="row" style={{ justifyContent: "space-between", marginTop: 10 }}>
              <div>
                <div className="kpiLabel">val_acc</div>
                <div className="kpiValue">{current.metrics_json?.val_accuracy ?? "—"}</div>
              </div>
              <div>
                <div className="kpiLabel">val_loss</div>
                <div className="kpiValue">{current.metrics_json?.val_loss ?? "—"}</div>
              </div>
            </div>
            <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
              <div>
                <div className="kpiLabel">Accuracy</div>
                <Sparkline values={accHistory} />
              </div>
              <div>
                <div className="kpiLabel">Loss</div>
                <Sparkline values={lossHistory} />
              </div>
            </div>
          </>
        ) : (
          <div className="muted">Chưa có run.</div>
        )}
      </div>

      <div className="card" style={{ gridColumn: "1 / -1" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Events</h3>
          <div className="muted">{selected ? `run ${selected.slice(0, 8)}` : ""}</div>
        </div>
        <div className="events">
          {events.length === 0 ? <div className="muted">Chưa có event.</div> : null}
          {events.map((e) => (
            <div key={e.id} className="eventRow">
              <span className={`dot ${e.level === "ERROR" ? "danger" : "info"}`} />
              <span className="mono">{new Date(e.ts).toLocaleString()}</span>
              <span className="mono">{e.level}</span>
              <span>{e.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Data() {
  const [dataset, setDataset] = useState("mosquitodl")
  const [maxPerLabel, setMaxPerLabel] = useState(500)
  const [valRatio, setValRatio] = useState(0.1)
  const [testRatio, setTestRatio] = useState(0.1)
  const [seed, setSeed] = useState(42)

  const [jobs, setJobs] = useState([])
  const [selected, setSelected] = useState(null)
  const [events, setEvents] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  async function loadJobs() {
    const resp = await apiFetch("/admin/data/jobs?limit=50")
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    setJobs(data)
    if (!selected && data[0]) setSelected(data[0].id)
  }

  async function loadEvents(jobId) {
    if (!jobId) return
    const resp = await apiFetch(`/admin/data/jobs/${jobId}/events?limit=200`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    setEvents(data)
  }

  async function refresh() {
    setErr("")
    try {
      await loadJobs()
    } catch (e) {
      setErr(String(e?.message || e))
    }
  }

  useEffect(() => {
    refresh()
  }, [])
  useInterval(() => refresh(), 3000)
  useInterval(() => loadEvents(selected).catch(() => {}), 2000)

  const current = useMemo(() => jobs.find((j) => j.id === selected) || null, [jobs, selected])

  async function start(kind) {
    setErr("")
    setBusy(true)
    try {
      const path = kind === "download" ? "/admin/data/download" : "/admin/data/preprocess"
      const resp = await apiFetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset,
          max_per_label: Number(maxPerLabel) || 500,
          val_ratio: Number(valRatio) || 0.1,
          test_ratio: Number(testRatio) || 0.1,
          seed: Number(seed) || 42,
        }),
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `HTTP ${resp.status}`)
      }
      await refresh()
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid2">
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Tải dữ liệu</h3>
        <div className="muted">Dataset hiện hỗ trợ: MosquitoDL (public GitHub).</div>
        <label className="label" style={{ marginTop: 10 }}>
          Dataset
          <select className="select" value={dataset} onChange={(e) => setDataset(e.target.value)}>
            <option value="mosquitodl">mosquitodl</option>
          </select>
        </label>
        {err ? <div className="alert danger">{err}</div> : null}
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn primary" disabled={busy} onClick={() => start("download")}>
            {busy ? "Đang chạy..." : "Download"}
          </button>
          <button className="btn" onClick={refresh}>
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Preprocess</h3>
        <div className="muted">Tạo `data/processed/mosquitodl/{train,val,test}/(label)/` (copy file).</div>
        <div className="formGrid" style={{ marginTop: 10 }}>
          <label className="label">
            Max / label
            <input className="input" type="number" min={1} value={maxPerLabel} onChange={(e) => setMaxPerLabel(e.target.value)} />
          </label>
          <label className="label">
            Seed
            <input className="input" type="number" min={0} value={seed} onChange={(e) => setSeed(e.target.value)} />
          </label>
          <label className="label">
            Val ratio
            <input className="input" type="number" step="0.01" min={0} max={0.5} value={valRatio} onChange={(e) => setValRatio(e.target.value)} />
          </label>
          <label className="label">
            Test ratio
            <input className="input" type="number" step="0.01" min={0} max={0.5} value={testRatio} onChange={(e) => setTestRatio(e.target.value)} />
          </label>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn primary" disabled={busy} onClick={() => start("preprocess")}>
            {busy ? "Đang chạy..." : "Preprocess"}
          </button>
        </div>
      </div>

      <div className="card" style={{ gridColumn: "1 / -1" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Jobs</h3>
          <div className="row" style={{ alignItems: "center" }}>
            <select className="select" value={selected || ""} onChange={(e) => setSelected(e.target.value)}>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.kind} {j.id}
                </option>
              ))}
            </select>
            <button className="btn" onClick={() => loadEvents(selected).catch(() => {})}>
              Load events
            </button>
          </div>
        </div>

        {current ? (
          <div style={{ marginTop: 12 }}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div className="mono">{current.id}</div>
                <div className="muted">{current.kind}</div>
                <span className={`badge ${statusColor(current.status)}`}>{current.status}</span>
              </div>
              <ProgressRing value={current.progress} />
            </div>
            <div style={{ marginTop: 10 }} className="bar">
              <div className="barFill" style={{ width: `${current.progress}%` }} />
            </div>
            {current.error_message ? <div className="alert danger">{current.error_message}</div> : null}
            {current.result_json ? (
              <pre style={{ marginTop: 12, maxHeight: 260 }}>{JSON.stringify(current.result_json, null, 2)}</pre>
            ) : null}
          </div>
        ) : (
          <div className="muted" style={{ marginTop: 12 }}>
            Chưa có job.
          </div>
        )}

        <div className="events" style={{ marginTop: 12 }}>
          {events.map((e) => (
            <div key={e.id} className="eventRow">
              <span className={`dot ${e.level === "ERROR" ? "danger" : "info"}`} />
              <span className="mono">{new Date(e.ts).toLocaleString()}</span>
              <span className="mono">{e.level}</span>
              <span>{e.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Config() {
  const [cfg, setCfg] = useState({})
  const [draft, setDraft] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  async function load() {
    setErr("")
    const resp = await apiFetch("/admin/config")
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    setCfg(data)
    setDraft(data)
  }

  useEffect(() => {
    load().catch((e) => setErr(String(e?.message || e)))
  }, [])

  async function save() {
    setErr("")
    setBusy(true)
    try {
      const resp = await apiFetch("/admin/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `HTTP ${resp.status}`)
      }
      await load()
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setBusy(false)
    }
  }

  function setKey(key, value) {
    setDraft((d) => ({ ...d, [key]: value }))
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0 }}>Cấu hình</h3>
          <div className="muted">Lưu các tham số vận hành/training (KV JSON).</div>
        </div>
        <div className="row">
          <button className="btn" onClick={() => load().catch(() => {})}>
            Reload
          </button>
          <button className="btn primary" disabled={busy} onClick={save}>
            {busy ? "Đang lưu..." : "Lưu thay đổi"}
          </button>
        </div>
      </div>
      {err ? <div className="alert danger">{err}</div> : null}

      <div style={{ marginTop: 12 }} className="table">
        <div className="tr th">
          <div>Key</div>
          <div>Value (JSON)</div>
        </div>
        {Object.keys(draft).length === 0 ? <div className="muted">Chưa có config.</div> : null}
        {Object.entries(draft).map(([k, v]) => (
          <div key={k} className="tr">
            <div className="mono">{k}</div>
            <div>
              <textarea
                className="input mono"
                rows={3}
                value={JSON.stringify(v, null, 2)}
                onChange={(e) => {
                  try {
                    setKey(k, JSON.parse(e.target.value))
                  } catch {
                    setKey(k, { value: e.target.value })
                  }
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="muted" style={{ marginTop: 10 }}>
        Gợi ý key: <span className="mono">training.defaults</span>, <span className="mono">thresholds</span>, <span className="mono">ui</span>
      </div>
    </div>
  )
}

function Logs() {
  const [service, setService] = useState("backend")
  const [tail, setTail] = useState(200)
  const [lines, setLines] = useState([])
  const [error, setError] = useState("")

  async function loadLogs() {
    setError("")
    try {
      const resp = await apiFetch(`/admin/logs?service=${service}&tail=${tail}`)
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
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Logs</h3>
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
      </div>
      {error ? <div className="alert danger">{error}</div> : null}
      <pre style={{ marginTop: 12, maxHeight: 520 }}>{lines.join("\n")}</pre>
    </div>
  )
}
