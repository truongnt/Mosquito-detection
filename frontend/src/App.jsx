import React from "react"
import { NavLink, Route, Routes } from "react-router-dom"
import Home from "./pages/Home.jsx"
import Admin from "./pages/Admin.jsx"

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
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </div>
  )
}
