import { defineConfig, devices } from '@playwright/test'

// Run `npm run build` first: the smoke tests exercise the built site with the example and the empty fixture releases.
export default defineConfig({
  testDir: 'e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: { trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: 'node scripts/serve.mjs --site dist --data fixtures/example/data --port 4173', url: 'http://127.0.0.1:4173/', reuseExistingServer: !process.env.CI },
    { command: 'node scripts/serve.mjs --site dist --data fixtures/empty/data --port 4174', url: 'http://127.0.0.1:4174/', reuseExistingServer: !process.env.CI },
  ],
})
