import { test, expect } from "@playwright/test";
test("mobile navigation fits viewport and dialogs close by keyboard", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/catalog");
  await expect(
    page.getByRole("button", { name: "Workspace", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Workspace", exact: true }).click();
  await page.getByRole("link", { name: "Domains", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Business domains" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Details" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const dimensions = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(dimensions.width).toBeLessThanOrEqual(dimensions.viewport);
});
test("project edits persist and analyst sees read-only metadata", async ({
  page,
}) => {
  await page.goto("/projects");
  await page
    .getByRole("button", {
      name: "Edit Counterparty Risk Intelligence delivery",
      exact: true,
    })
    .click();
  await page.getByLabel("Project budget").fill("");
  await page
    .getByLabel("Project budget")
    .pressSequentially("975000", { delay: 30 });
  await expect(page.getByLabel("Project budget")).toHaveValue("975000");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByText("Changes saved", { exact: true })).toBeVisible();
  await page.reload();
  await expect(
    page
      .getByRole("row")
      .filter({
        has: page.getByText("Counterparty Risk Intelligence delivery", {
          exact: true,
        }),
      })
      .getByText("$975,000", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Demo persona").selectOption("analyst");
  await expect(
    page.getByText("Your demo role has read access.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Edit Counterparty Risk Intelligence delivery",
      exact: true,
    }),
  ).toHaveCount(0);
});

test("workspace readiness identifies unavailable services and request errors", async ({
  page,
}) => {
  let failed = false;
  await page.route("**/api/health", (route) =>
    route.fulfill(
      failed
        ? { status: 503, json: { detail: "Health endpoint unavailable" } }
        : {
            json: {
              services: {
                postgres: { status: "ready" },
                minio: { status: "unavailable" },
                fuseki: { status: "ready" },
                opensearch: { status: "ready" },
              },
            },
          },
    ),
  );
  await page.goto("/catalog");
  await page.getByRole("button", { name: "Workspace", exact: true }).click();
  await expect(
    page.getByText("MinIO · unavailable", { exact: true }),
  ).toBeVisible();
  failed = true;
  await page.reload();
  await page.getByRole("button", { name: "Workspace", exact: true }).click();
  await expect(
    page.getByText("Unable to check service readiness", { exact: true }),
  ).toBeVisible();
});
