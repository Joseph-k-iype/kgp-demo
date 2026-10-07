import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 90000,
  expect: { timeout: 20000 },
  use: { baseURL: "http://127.0.0.1:53000", headless: true },
  workers: 1,
  reporter: "list",
});
