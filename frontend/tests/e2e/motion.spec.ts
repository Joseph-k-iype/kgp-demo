import { test, expect } from "@playwright/test";
test("reduced motion keeps search and nested details keyboard usable", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Find knowledge. Understand it." }),
  ).toBeVisible();
  await page.getByRole("searchbox").fill("counterparty");
  await page.getByRole("link", { name: "Catalog", exact: true }).click();
  await page.getByLabel("Filter by domain").selectOption("risk");
  const card = page.getByRole("button", {
    name: "Counterparty Risk Intelligence",
    exact: true,
  });
  await card.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("dialog").getByRole("button", { name: "Close dialog" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(card).toBeFocused();
  await page
    .getByRole("link", { name: "Knowledge Product Manager", exact: true })
    .click();
  await expect(page.getByRole("searchbox")).toBeEnabled();
  expect(
    await page
      .locator(".home-introduction h1")
      .evaluate((el) => getComputedStyle(el).transform),
  ).toBe("none");
});
test("route changes during the introduction leave returning search interactive", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Catalog", exact: true }).click();
  await page
    .getByRole("link", { name: "Knowledge Product Manager", exact: true })
    .click();
  await page.getByRole("searchbox").fill("treasury");
  await expect(page.getByRole("searchbox")).toHaveValue("treasury");
  await expect(page.locator(".home-introduction h1")).toHaveCSS("opacity", "1");
});
