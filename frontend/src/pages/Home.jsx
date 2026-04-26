import React, { useState } from "react"
import { apiBase } from "../api.js"

export default function Home() {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState("")

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
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setError(String(err?.message || err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <h2>Nhận dạng muỗi</h2>
      <p className="muted">Upload 1 ảnh và nhận dự đoán (hiện demo stub).</p>
      <form onSubmit={onSubmit} className="row">
        <input className="input" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <button className="btn primary" disabled={busy}>
          {busy ? "Đang xử lý..." : "Nhận dạng"}
        </button>
      </form>

      {error ? (
        <p style={{ color: "#dc2626" }}>{error}</p>
      ) : null}

      {result ? (
        <div style={{ marginTop: 12 }}>
          <div className="row">
            <div className="card" style={{ flex: "1 1 280px" }}>
              <div className="muted">Request</div>
              <div>{result.request_id}</div>
            </div>
            <div className="card" style={{ flex: "1 1 280px" }}>
              <div className="muted">Kết quả</div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{result.result.label}</div>
              <div className="muted">confidence: {result.result.confidence}</div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
