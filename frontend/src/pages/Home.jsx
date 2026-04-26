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
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState("")
  const [previewUrl, setPreviewUrl] = useState("")

  useEffect(() => {
    if (!file) {
      setPreviewUrl("")
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const conf = useMemo(() => confidencePct(result?.result?.confidence), [result])

  async function onSubmit(e) {
    e.preventDefault()
    setError("")
    setResult(null)
    if (!file) {
      setError("Chọn 1 ảnh trước khi gửi.")
      return
    }
    setBusy(true)
    try {
      const form = new FormData()
      form.append("image", file)
      const resp = await fetch(`${apiBase()}/predict`, { method: "POST", body: form, credentials: "include" })
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
            Tải 1 ảnh muỗi, hệ thống sẽ dự đoán loài (classification) và trả về mức độ tin cậy.
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
            <div className="dropZone">
              <div>
                <div style={{ fontWeight: 800 }}>Chọn ảnh</div>
                <div className="muted">JPEG/PNG/WebP</div>
              </div>
              <input
                className="input"
                type="file"
                accept="image/*"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                style={{ flex: "1 1 auto" }}
              />
            </div>

            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <button className="btn primary" disabled={busy || !file}>
                {busy ? "Đang nhận dạng..." : "Nhận dạng"}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setFile(null)
                  setResult(null)
                  setError("")
                }}
                disabled={busy && !file}
              >
                Reset
              </button>
            </div>
          </form>

          {error ? <div className="alert danger">{error}</div> : null}

          {previewUrl ? (
            <div style={{ marginTop: 12 }}>
              <div className="muted">Preview</div>
              <img className="previewImg" src={previewUrl} alt="preview" />
            </div>
          ) : null}
        </div>

        <div className="card">
          <h2 style={{ marginTop: 0, marginBottom: 6 }}>Kết quả</h2>
          <div className="muted">Top-1 label + confidence.</div>

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
            <div className="resultBox">
              <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                <div>
                  <div className="kpiLabel">Label</div>
                  <div className="resultLabel">{result?.result?.label || "—"}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="kpiLabel">Confidence</div>
                  <div className="resultConf">{conf == null ? "—" : `${conf}%`}</div>
                </div>
              </div>

              <div className="bar" style={{ marginTop: 10 }}>
                <div className="barFill" style={{ width: `${conf || 0}%` }} />
              </div>
              <div className="muted" style={{ marginTop: 8 }}>
                request_id: <span className="mono">{result.request_id}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
