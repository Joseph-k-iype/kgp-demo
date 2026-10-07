import { test, expect } from "@playwright/test";
test("extractive search shows trace and cited evidence", async ({ page }) => {
  await page.goto("/search");
  await page.getByLabel("Search mode").selectOption("extractive");
  await page
    .getByLabel("Ask a knowledge question")
    .fill("counterparty exposure due diligence");
  await page
    .getByRole("button", { name: "Search knowledge", exact: true })
    .click();
  await expect(page.getByText("Search completed", { exact: true })).toBeVisible(
    { timeout: 85000 },
  );
  await expect(
    page.getByText("Extractive demo:", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open evidence 1", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open evidence 1", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Source evidence", exact: true }),
  ).toBeVisible();
});
