import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// base './' — the site works from any sub-path (GitHub Pages) and data is fetched relative to it.
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  server: { port: 3000 },
})
