import React from "react"
import { NavLink, Route, Routes } from "react-router-dom"
import Home from "./pages/Home.jsx"
import AdminLogin from "./pages/AdminLogin.jsx"
import AdminPanel from "./pages/AdminPanel.jsx"

export default function App() {
  return (
    <div className="container">
      <div className="nav">
        <NavLink to="/" className={({ isActive }) => (isActive ? "link active" : "link")}>
          Nhận dạng
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => (isActive ? "link active" : "link")}>
          Quản trị
        </NavLink>
      </div>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </div>
  )
}
