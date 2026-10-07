import { test, expect } from "@playwright/test";

test("search home is a focused entry point with all authorized domains", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Find knowledge. Understand it." }),
  ).toBeVisible();
  await expect(
    page.getByRole("searchbox", { name: "Search enterprise knowledge" }),
  ).toHaveCount(1);
  await expect(page.locator(".sidebar")).toHaveCount(0);
  await expect(page.locator(".stats")).toHaveCount(0);
  await expect(page.getByLabel("Search domain").locator("option")).toHaveCount(
    12,
  );
  await page.getByRole("button", { name: "Workspace", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Ontology explorer", exact: true }),
  ).toBeVisible();
});

test("keyboard search preserves query and domain without submitting composition", async ({
  page,
}) => {
  await page.goto("/");
  const search = page.getByRole("searchbox", {
    name: "Search enterprise knowledge",
  });
  await search.fill("counterparty exposure");
  await search.dispatchEvent("compositionstart");
  await search.press("Enter");
  await expect(page).toHaveURL(/53000\/$/);
  await search.dispatchEvent("compositionend");
  await page.getByLabel("Search domain").selectOption("risk");
  await search.press("Enter");
  await expect(page).toHaveURL(
    /\/search\?.*q=counterparty\+exposure.*domain_id=risk/,
  );
});

test("a query is not lost while the search form hydrates", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(/\/_next\/static\/.*\.js/, async (route) => {
    await gate;
    await route.continue();
  });
  try {
    await page.goto("/", { waitUntil: "commit" });
    const search = page.getByRole("searchbox", {
      name: "Search enterprise knowledge",
    });
    await search.waitFor();
    const guarded = await search.isDisabled();
    if (!guarded) await search.fill("counterparty exposure");
    release();
    await expect(search).toBeEnabled();
    if (guarded) await search.fill("counterparty exposure");
    await expect(search).toHaveValue("counterparty exposure");
    await search.press("Enter");
    await expect(page).toHaveURL(/\/search\?.*q=counterparty\+exposure/);
  } finally {
    release();
  }
});
