import { defineConfig, devices } from "@playwright/test";

const viewports = [
  ["desktop-1460x880", 1460, 880],
  ["desktop-1280x720", 1280, 720],
  ["stacked-1120x720", 1120, 720],
  ["stacked-920x680", 920, 680],
  ["single-820x720", 820, 720],
];

export default defineConfig({
  testDir: "./scripts/playwright",
  outputDir: "./assets/resource/ShiKong/reports/playwright-workbench/results",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: "./assets/resource/ShiKong/reports/playwright-workbench/report.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:4173",
    ...devices["Desktop Edge"],
    channel: "msedge",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    navigationTimeout: 60_000,
    actionTimeout: 15_000,
  },
  webServer: {
    command: "npm run build && npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 180_000,
  },
  projects: viewports.map(([name, width, height]) => ({
    name,
    use: { viewport: { width, height } },
  })),
});
