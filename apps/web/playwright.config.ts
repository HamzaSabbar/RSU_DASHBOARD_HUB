import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  // Local dev boxes running this suite alongside an IDE, browser, and other
  // tooling can see multi-second CPU scheduling delays that dwarf actual
  // page-render time; a generous timeout plus one retry absorbs that without
  // loosening any assertion (a genuine app hang still fails after retrying).
  timeout: 60_000,
  retries: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
  ],
});
