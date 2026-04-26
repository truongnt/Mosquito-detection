import React, { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { apiBase } from "../api.js"

function confidencePct(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return null
  return Math.max(0, Math.min(100, Math.round(n * 100)))
}

async function readError(resp) {
  const ct = resp.headers.get("content-type") || ""
  try {
    if (ct.includes("application/json")) {
      const j = await resp.json()
      const d = j?.detail
      if (typeof d === "string") return d
      if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join("\n")
      return JSON.stringify(j)
    }
    const t = await resp.text()
    return t || `HTTP ${resp.status}`
  } catch {
    return `HTTP ${resp.status}`
  }
}

export default function Home() {
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState("")
  const [previewUrls, setPreviewUrls] = useState([])
  const [models, setModels] = useState([])
  const [selectedModels, setSelectedModels] = useState(["yolo"])

  useEffect(() => {
    if (!files.length) {
      setPreviewUrls([])
      return
    }
    const urls = files.map((f) => URL.createObjectURL(f))
    setPreviewUrls(urls)
    return () => urls.forEach((u) => URL.revokeObjectURL(u))
  }, [files])

  useEffect(() => {
    async function loadModels() {
      try {
        const resp = await fetch(`${apiBase()}/models`, { credentials: "include" })
        if (!resp.ok) return
        const data = await resp.json()
        if (Array.isArray(data) && data.length) {
          setModels(data)
          const ids = data.map((m) => m.id).filter(Boolean)
          setSelectedModels((prev) => (prev?.length ? prev.filter((x) => ids.includes(x)) : ["yolo"]))
        }
      } catch {
        // ignore
      }
    }
    loadModels()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const resultsByModel = useMemo(() => {
    const arr = result?.results
    if (!Array.isArray(arr)) return []
    return arr
  }, [result])

  async function onSubmit(e) {
    e.preventDefault()
    setError("")
    setResult(null)
    if (!files.length) {
      setError("Chọn ít nhất 1 ảnh trước khi gửi.")
      return
    }
    setBusy(true)
    try {
      const form = new FormData()
      files.forEach((f) => form.append("images", f))
      form.append("models", JSON.stringify(selectedModels.length ? selectedModels : ["yolo"]))
      const resp = await fetch(`${apiBase()}/predict_multi`, { method: "POST", body: form, credentials: "include" })
      if (!resp.ok) throw new Error(await readError(resp))
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setError(String(err?.message || err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="homeShell">
      <div className="hero card">
        <div className="heroLeft">
          <div className="heroTitle">Mosquito AI</div>
          <div className="heroSub muted">
            Tải 1 hoặc nhiều ảnh muỗi, chọn 1 hoặc nhiều model, hệ thống sẽ dự đoán loài (classification) và trả về mức độ tin cậy.
          </div>
          <div className="row" style={{ marginTop: 10, alignItems: "center" }}>
            <Link className="btn" to="/admin/login">
              Admin
            </Link>
            <div className="muted">
              API: <span className="mono">{apiBase()}</span>
            </div>
          </div>
        </div>
        <div className="heroRight">
          <div className="kpiLabel">Trạng thái</div>
          <div className={`badge ${busy ? "info" : "success"}`}>{busy ? "Đang xử lý" : "Sẵn sàng"}</div>
          {result?.request_id ? <div className="muted">request {result.request_id.slice(0, 10)}</div> : null}
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h2 style={{ marginTop: 0, marginBottom: 6 }}>Nhận dạng</h2>
          <div className="muted">Ảnh rõ nét, cắt sát muỗi, nền đơn giản sẽ cho kết quả tốt hơn.</div>

          <form onSubmit={onSubmit} style={{ marginTop: 12, display: "grid", gap: 10 }}>
            <div className="miniCard">
              <div style={{ fontWeight: 800 }}>Chọn model</div>
              <div className="muted">Bạn có thể so sánh kết quả của nhiều model cùng lúc.</div>
              <div className="row" style={{ marginTop: 10 }}>
                {(models.length ? models : [{ id: "yolo", name: "YOLO (active)" }]).map((m) => (
                  <label key={m.id} className="row" style={{ alignItems: "center", gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={selectedModels.includes(m.id)}
                      onChange={(e) => {
                        const checked = e.target.checked
                        setSelectedModels((prev) => {
                          const set = new Set(prev)
                          if (checked) set.add(m.id)
                          else set.delete(m.id)
                          const next = Array.from(set)
                          return next.length ? next : ["yolo"]
                        })
                      }}
                    />
                    <span style={{ fontWeight: 700 }}>{m.name || m.id}</span>
                    {m.noncommercial_only ? <span className="badge danger">NC</span> : null}
                  </label>
                ))}
              </div>
              <div className="muted" style={{ marginTop: 8 }}>
                Selected: <span className="mono">{selectedModels.join(", ")}</span>
              </div>
            </div>

            <div className="dropZone">
              <div>
                <div style={{ fontWeight: 800 }}>Chọn ảnh</div>
                <div className="muted">JPEG/PNG/WebP (có thể chọn nhiều)</div>
              </div>
              <input
                className="input"
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
                style={{ flex: "1 1 auto" }}
              />
            </div>

            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <button className="btn primary" disabled={busy || !files.length}>
                {busy ? "Đang nhận dạng..." : "Nhận dạng"}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setFiles([])
                  setResult(null)
                  setError("")
                }}
                disabled={busy && !files.length}
              >
                Reset
              </button>
            </div>
          </form>

          {error ? <div className="alert danger">{error}</div> : null}

          {previewUrls.length ? (
            <div style={{ marginTop: 12 }}>
              <div className="muted">Preview ({previewUrls.length})</div>
              <div className="previewGrid">
                {previewUrls.slice(0, 6).map((u, idx) => (
                  <img key={u} className="previewThumb" src={u} alt={`preview-${idx}`} />
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="card">
          <h2 style={{ marginTop: 0, marginBottom: 6 }}>Kết quả</h2>
          <div className="muted">Top-1 label + confidence (theo từng model).</div>

          {!result ? (
            <div className="emptyState">
              <div className="emptyTitle">Chưa có kết quả</div>
              <div className="muted">Chọn ảnh và bấm “Nhận dạng”.</div>
              <div className="miniCard" style={{ marginTop: 12 }}>
                <div className="muted">Gợi ý khi gặp lỗi 503</div>
                <div className="muted">Model chưa sẵn sàng → vào Admin để chạy Preprocess/Training.</div>
              </div>
            </div>
          ) : (
            <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
              {resultsByModel.map((r) => {
                const conf = confidencePct(r?.confidence)
                return (
                  <div key={r.model_id} className="resultBox">
                    <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                      <div>
                        <div className="kpiLabel">Model</div>
                        <div className="mono" style={{ fontWeight: 900 }}>
                          {r.model_id}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div className="kpiLabel">Confidence</div>
                        <div className="resultConf">{conf == null ? "—" : `${conf}%`}</div>
                      </div>
                    </div>

                    <div style={{ marginTop: 8 }}>
                      <div className="kpiLabel">Label</div>
                      <div className="resultLabel">{r?.label || "—"}</div>
                    </div>

                    <div className="bar" style={{ marginTop: 10 }}>
                      <div className="barFill" style={{ width: `${conf || 0}%` }} />
                    </div>
                  </div>
                )
              })}
              <div className="muted">
                request_id: <span className="mono">{result.request_id}</span> • images: <span className="mono">{files.length}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
