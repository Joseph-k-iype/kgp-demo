import { test, expect } from "@playwright/test";
test("catalog filters persist and real sources preview", async ({ page }) => {
  await page.goto("/catalog");
  await expect(
    page.getByRole("heading", { name: "Knowledge catalog", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Filter by domain").selectOption("risk");
  await expect(page.getByText("4 products", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/domain_id=risk/);
  await page.reload();
  await expect(page.getByLabel("Filter by domain")).toHaveValue("risk");
  await page
    .getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "counterparty_exposure", exact: true })
    .click();
  await page.getByRole("button", { name: "Preview source" }).click();
  await expect(page.getByText("Aster Capital").first()).toBeVisible();
});
test("all domains and ontology graph are navigable", async ({ page }) => {
  await page.goto("/domains");
  await expect(
    page.getByRole("heading", { name: "Risk and Compliance", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Finance Treasury and Enterprise Tax",
      exact: true,
    }),
  ).toBeVisible();
  await page.goto("/ontology");
  await expect(
    page.getByRole("heading", { name: "Ontology explorer", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "List view" }).click();
  await expect(
    page.getByText("Counterparty", { exact: true }).first(),
  ).toBeVisible();
});

test("global search updates same-route filters and browser back restores them", async ({
  page,
}) => {
  await page.goto("/catalog");
  await page.getByLabel("Filter by domain").selectOption("risk");
  await expect(page.getByText("4 products", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/domain_id=risk/);
  await page.getByLabel("Global catalog search").fill("Counterparty");
  await page.getByLabel("Global catalog search").press("Enter");
  await expect(page.locator("#catalog-search")).toHaveValue("Counterparty");
  await expect(
    page.getByRole("button", { name: "Counterparty Master", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page.getByLabel("Filter by domain")).toHaveValue("risk");
  await expect(page.locator("#catalog-search")).toHaveValue("");
});
