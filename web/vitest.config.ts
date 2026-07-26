import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Vitest loads this in preference to vite.config.ts. Kept separate so the app's
// vite build config stays typechecked against the installed Vite while the test
// runner uses Vitest's bundled toolchain.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
