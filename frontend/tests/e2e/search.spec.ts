import { test, expect } from "@playwright/test";
test("source-only search shows real trace and cited evidence", async ({
  page,
}) => {
  await page.goto("/search?q=counterparty+exposure+due+diligence");
  await page.getByText("Answer options", { exact: true }).click();
  await page
    .getByRole("button", { name: "Use source excerpts", exact: true })
    .click();
  await expect(page.locator(".answer-content")).toBeVisible({ timeout: 85000 });
  await expect(
    page.getByText("Extractive demo:", { exact: false }).first(),
  ).toBeVisible();
  await page.getByText("Search steps", { exact: true }).click();
  await expect(
    page.getByText("Search completed with validated citations", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /^Open source:/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("counterparty", {
    ignoreCase: true,
  });
  await page.getByRole("tab", { name: "Context", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("Source provenance");
});
