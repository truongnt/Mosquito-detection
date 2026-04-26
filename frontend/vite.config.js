import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const target = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000"

  return {
    plugins: [react()],
    server: {
      port: 3000,
      host: true,
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
