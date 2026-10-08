import { test, expect } from "@playwright/test";

test("library filters and view persist and real structured sources preview", async ({
  page,
}) => {
  await page.goto("/catalog");
  await expect(
    page.getByRole("heading", { name: "Knowledge catalog", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Grid view", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Filter by domain").selectOption("risk");
  await expect(page.getByText("4 products", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/domain_id=risk/);
  await page.getByRole("button", { name: "List view", exact: true }).click();
  await page.reload();
  await expect(page.getByLabel("Filter by domain")).toHaveValue("risk");
  await expect(
    page.getByRole("button", { name: "List view", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("tab", { name: "Assets", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "counterparty_exposure", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .last()
    .getByRole("button", { name: "Preview source", exact: true })
    .click();
  await expect(
    page
      .getByRole("dialog")
      .last()
      .getByText("Aster Capital", { exact: true })
      .first(),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    }),
  ).toBeFocused();
});

test("product details reveal real documents governance and projects on demand", async ({
  page,
}) => {
  await page.goto("/catalog?domain_id=risk");
  await page
    .getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    })
    .click();
  const product = page.getByRole("dialog").first();
  await expect(product).toContainText("Priya Shah");
  await product.getByRole("tab", { name: "Ontology", exact: true }).click();
  await expect(
    product.getByRole("link", { name: /Counterparty/ }).first(),
  ).toBeVisible();
  await product.getByRole("tab", { name: "Projects", exact: true }).click();
  await expect(product).toContainText(
    "Counterparty Risk Intelligence delivery",
  );
  await product.getByRole("tab", { name: "Assets", exact: true }).click();
  await product
    .getByRole("button", { name: /Counterparty due diligence policy/i })
    .click();
  const source = page.getByRole("dialog").last();
  await source
    .getByRole("button", { name: "Preview source", exact: true })
    .click();
  await expect(source).toContainText("Original source preview");
  await expect(source.locator(".source-code")).toContainText(
    "Synthetic enterprise evidence",
  );
  await expect(source).toContainText("MinIO");
});

test("catalog search opens combined discovery and browser back restores library filters", async ({
  page,
}) => {
  await page.goto("/catalog?domain_id=risk&view=list");
  await page.route("**/api/search/runs", (route) =>
    route.fulfill({
      json: {
        run_id: "catalog-query",
        status: "failed",
        query: "counterparty",
        mode: "llm",
        domain_id: "risk",
        statements: [],
        evidence: [],
        events: [],
        gaps: [],
        graph: { nodes: [], edges: [] },
        error: "Test provider unavailable",
      },
    }),
  );
  await page
    .getByRole("searchbox", { name: "Search enterprise knowledge" })
    .fill("counterparty");
  await page
    .getByRole("button", { name: "Search knowledge", exact: true })
    .click();
  await expect(page).toHaveURL(/\/search\?.*q=counterparty.*domain_id=risk/);
  await page.goBack();
  await expect(page.getByLabel("Filter by domain")).toHaveValue("risk");
  await expect(
    page.getByRole("button", { name: "List view", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("all domains and ontology graph remain navigable", async ({ page }) => {
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
  await page.getByRole("button", { name: "List view", exact: true }).click();
  await expect(
    page.getByText("Counterparty", { exact: true }).first(),
  ).toBeVisible();
});
