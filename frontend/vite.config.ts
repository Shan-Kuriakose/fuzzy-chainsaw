import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  root: new URL('.', import.meta.url).pathname,
  plugins: [react(), tailwindcss()],
})
