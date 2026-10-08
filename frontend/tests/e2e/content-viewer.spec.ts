import { test, expect } from "@playwright/test";

test("catalog opens real product rows immediately with one content surface", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (e) => failures.push(e.message));
  await page.goto("/catalog?domain_id=risk");
  await page
    .getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    })
    .click();
  const viewer = page.getByRole("dialog");
  await expect(viewer).toHaveCount(1);
  await expect(
    viewer.getByText("Aster Capital", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    viewer.getByRole("button", { name: "Preview source", exact: true }),
  ).toHaveCount(0);
  await expect(
    viewer.getByRole("tab", { name: "Context", exact: true }),
  ).toBeVisible();
  await viewer.getByRole("tab", { name: "Context", exact: true }).click();
  await expect(viewer).toContainText("Priya Shah");
  await viewer.getByRole("tab", { name: "Relationships", exact: true }).click();
  await expect(viewer).toContainText("Counterparty");
  await page.keyboard.press("Escape");
  await expect(viewer).toHaveCount(0);
  await expect(
    page.getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    }),
  ).toBeFocused();
  expect(failures).toEqual([]);
});

test("ontology uses React Flow with a current governing path and opens source content", async ({
  page,
}) => {
  await page.goto("/ontology?concept=treasury-liquidity");
  await expect(page.locator(".react-flow")).toBeVisible();
  await expect(page.locator(".react-flow__minimap-node").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Fit graph", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Graph layout direction")).toBeVisible();
  await expect(page.getByLabel("Find graph node")).toBeVisible();
  await page.getByLabel("Find graph node").fill("TL-POL-001");
  await page.getByRole("button", { name: /Focus.*TL-POL-001/ }).click();
  await page
    .getByRole("button", { name: "Open source content", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "reconcile liquidity positions daily",
  );
  await expect(page.getByRole("dialog")).toHaveCount(1);
});

test("content and context remain reachable on mobile without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/catalog?domain_id=risk");
  await page
    .getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    })
    .click();
  await expect(
    page
      .getByRole("dialog")
      .getByText("Aster Capital", { exact: true })
      .first(),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Context", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("Priya Shah");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("source errors remain explicit and unsafe document markup never executes", async ({
  page,
}) => {
  await page.route("**/api/products/risk-product-0/content?**", (route) =>
    route.fulfill({
      json: {
        handle: { kind: "product", id: "risk-product-0" },
        title: "Source policy",
        content_type: "document",
        text: "# Source policy\n\n<script>window.unsafeSourceRan=true</script>\n\n[Unsafe link](javascript:alert(1))\n\n![Remote image](https://example.invalid/tracking.png)\n\nReadable policy clause.",
        has_more: false,
        truncated: false,
        freshness: "current",
        context: {},
      },
    }),
  );
  await page.goto("/catalog?domain_id=risk&selected=risk-product-0");
  await expect(page.getByRole("dialog")).toContainText(
    "Readable policy clause.",
  );
  expect(await page.evaluate(() => "unsafeSourceRan" in window)).toBe(false);
  await expect(
    page
      .getByRole("dialog")
      .locator(".source-markdown img, .source-markdown a"),
  ).toHaveCount(0);
  await page.keyboard.press("Escape");
  await page.unroute("**/api/products/risk-product-0/content?**");
  await page.route("**/api/products/risk-product-0/content?**", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Document store unavailable" },
    }),
  );
  await page
    .getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "Document store unavailable",
  );
  await expect(page.getByRole("dialog")).not.toContainText(
    "No matching knowledge",
  );
});

test("switching sources discards delayed content and retains one dialog", async ({
  page,
}) => {
  const base = {
    handle: { kind: "product", id: "risk-product-0" },
    content_type: "document",
    has_more: false,
    truncated: false,
    freshness: "current",
    context: {},
    manifest: {
      product_id: "risk-product-0",
      title: "Risk knowledge",
      primary: { kind: "asset", id: "initial" },
      sources: [
        {
          title: "Initial source",
          source_type: "Document",
          handle: { kind: "asset", id: "initial" },
        },
        {
          title: "Delayed source",
          source_type: "Document",
          handle: { kind: "asset", id: "slow" },
        },
        {
          title: "Current source",
          source_type: "Document",
          handle: { kind: "asset", id: "current" },
        },
      ],
      truncated: false,
    },
  };
  await page.route(
    "**/api/products/risk-product-0/content?**",
    async (route) => {
      const source =
        new URL(route.request().url()).searchParams.get("preferred_asset_id") ||
        "initial";
      if (source === "slow")
        await new Promise((resolve) => setTimeout(resolve, 1200));
      try {
        await route.fulfill({
          json: {
            ...base,
            title: source,
            text:
              source === "slow"
                ? "Obsolete source body"
                : source === "current"
                  ? "Current source body"
                  : "Initial source body",
          },
        });
      } catch {}
    },
  );
  await page.goto("/catalog?domain_id=risk&selected=risk-product-0");
  await expect(page.getByRole("dialog")).toContainText("Initial source body");
  const pending = page.waitForRequest((request) =>
    request.url().includes("preferred_asset_id=slow"),
  );
  await page.getByLabel("Product source").selectOption("slow");
  await pending;
  await expect(page.getByLabel("Product source")).toBeVisible({ timeout: 300 });
  await page.getByLabel("Product source").selectOption("current");
  await expect(page.getByRole("dialog")).toContainText("Current source body");
  await page.waitForTimeout(1500);
  await expect(page.getByRole("dialog")).not.toContainText(
    "Obsolete source body",
  );
  await expect(page.getByRole("dialog")).toHaveCount(1);
});

test("ontology filters domains and highlights the selected evidence path", async ({
  page,
}) => {
  await page.goto("/ontology?concept=treasury-liquidity");
  await expect(page.getByLabel("Graph domain")).toBeVisible();
  await page.getByLabel("Graph domain").selectOption("finance");
  await page.getByLabel("Find graph node").fill("TL-POL-001");
  await page.getByRole("button", { name: /Focus.*TL-POL-001/ }).click();
  await expect(
    page.locator(".react-flow__edge.evidence-path").first(),
  ).toBeVisible();
  await expect(page.getByText(/Selected source-backed path:/)).toContainText(
    "TL-POL-001",
  );
});

test("ontology handles cyclic, disconnected and empty neighborhoods", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const ref = {
    asset_id: "finance-asset-1",
    domain_id: "finance",
    locator: "controls",
    version: "fixture",
  };
  const node = (id: string) => ({
    id,
    name: id,
    kind: "BusinessEntity",
    domain_id: "finance",
    iri: "https://example.test/" + id,
    content_handle: { kind: "record", id },
  });
  await page.route("**/api/ontology/neighborhood?**", (route) =>
    route.fulfill({
      json: {
        root: "a",
        nodes: [node("a"), node("b"), node("c")],
        edges: [
          { source: "a", target: "b", label: "supportedBy", source_ref: ref },
          { source: "b", target: "a", label: "partOf", source_ref: ref },
        ],
        truncated: false,
      },
    }),
  );
  await page.goto("/ontology");
  await expect(page.locator(".react-flow__node")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Governing paths", exact: true })
    .click();
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Accessible list", exact: true })
    .click();
  await expect(
    page
      .locator(".ontology-accessible")
      .getByRole("button", { name: "c · BusinessEntity", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/ontology/neighborhood?**");
  await page.route("**/api/ontology/neighborhood?**", (route) =>
    route.fulfill({
      json: { root: "a", nodes: [], edges: [], truncated: false },
    }),
  );
  await page.goto("/ontology");
  await expect(page.locator(".ontology-legend")).toContainText(
    "0 nodes / 0 relationships",
  );
  expect(errors).toEqual([]);
});
