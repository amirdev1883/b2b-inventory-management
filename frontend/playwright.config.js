import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const python = process.env.E2E_PYTHON || 'python';
const database =
  process.env.E2E_DATABASE_URL || `sqlite:///${path.resolve('test-results/e2e.sqlite3')}`;
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `mkdir -p test-results && ${python} ../backend/manage.py migrate --noinput && ${python} ../backend/manage.py runserver 127.0.0.1:8000 --noreload`,
      url: 'http://127.0.0.1:8000/health/',
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: database,
        DJANGO_SETTINGS_MODULE: 'config.settings.dev',
        DJANGO_ALLOWED_HOSTS: '127.0.0.1,localhost',
        FRONTEND_URL: 'http://127.0.0.1:5173',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
