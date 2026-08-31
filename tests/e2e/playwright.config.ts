import { defineConfig } from '@playwright/test'

/**
 * EDU-085 — E2E Critical Journey (ARCHITECTURE.md §3, §26, §27).
 *
 * The suite exercises the existing vertical slice through the real UI:
 * Login → Dashboard → Teacher Environment → Course → Section → Learning Unit
 * → Activity → Draft → Preview → Publish.
 *
 * Playwright manages the application servers itself on dedicated ports so the
 * E2E run never collides with a running local Docker Compose stack:
 *
 * - frontend: built with Vite and served by `vite preview` on :4173
 * - backend:  migrations + uvicorn on :8100
 * - database: PostgreSQL on :5432 (started externally — Docker Compose or CI
 *   service container; see README.md)
 *
 * All origins are on `localhost` so the backend session cookie (SameSite=Lax)
 * flows between the frontend and the backend exactly as in the documented
 * local Docker setup.
 */

import path from 'node:path'

const repoRoot = path.resolve(import.meta.dirname, '../..')

const frontendPort = 4173
const backendPort = 8100

const frontendOrigin = `http://localhost:${frontendPort}`
const backendOrigin = `http://localhost:${backendPort}`

// Matches the local Docker Compose PostgreSQL defaults (see .env.example).
const databaseUrl =
  process.env.DATABASE_URL ??
  'postgresql+psycopg://education:local_development_only@localhost:5432/education_platform'

export default defineConfig({
  testDir: './specs',
  // One critical journey per run: serial, single worker, no parallelism.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: './test-results',
  use: {
    baseURL: frontendOrigin,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: `sh -c "alembic upgrade head && uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}"`,
      cwd: path.join(repoRoot, 'apps', 'backend'),
      env: {
        APP_ENV: 'development',
        DATABASE_URL: databaseUrl,
        FRONTEND_ORIGIN: frontendOrigin,
      },
      url: `${backendOrigin}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `sh -c "npm run build && npx vite preview --host 127.0.0.1 --port ${frontendPort} --strictPort"`,
      cwd: path.join(repoRoot, 'apps', 'frontend'),
      env: {
        VITE_API_BASE_URL: backendOrigin,
      },
      url: frontendOrigin,
      reuseExistingServer: false,
      timeout: 240_000,
    },
  ],
})
