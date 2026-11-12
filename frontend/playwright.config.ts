import {defineConfig, devices} from '@playwright/test';

const PORT = 4173;

/** E2E del flujo crítico: requiere la API en CPCMINI_API_URL (por defecto 127.0.0.1:8000). */
export default defineConfig({
  testDir: 'e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', {open: 'never'}]] : 'list',
  use: {baseURL: `http://127.0.0.1:${PORT}`, trace: 'retain-on-failure', locale: 'es-EC'},
  projects: [
    {name: 'escritorio', use: {...devices['Desktop Chrome']}},
    {name: 'movil', use: {...devices['Pixel 7']}},
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
