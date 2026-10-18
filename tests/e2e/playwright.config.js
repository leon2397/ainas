/**
 * Playwright E2E 测试配置
 */
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'reports/e2e' }],
    ['json', { outputFile: 'reports/e2e/results.json' }],
    ['list']
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // 配置模拟器 - Chromium
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // Firefox
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    // WebKit
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // 移动端模拟器 - iPhone
    {
      name: 'iPhone 13',
      use: { ...devices['iPhone 13'] },
    },

    // 移动端模拟器 - Android
    {
      name: 'Pixel 5',
      use: { ...devices['Pixel 5'] },
    },
  ],

  webServer: {
    command: 'npm run start',
    url: 'http://localhost:8000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },

  timeout: 30000,
  expect: {
    timeout: 10000
  }
});
