import { test, expect, Page } from "@playwright/test";
import type { DiscoveryItem } from "../../src/api/discovery";

type Options = {
  delayAI?: boolean;
  failAI?: boolean;
  failResults?: boolean;
  delayResults?: boolean;
  delayCancel?: boolean;
};
async function boundaries(page: Page, options: Options = {}) {
  let released = false;
  let cancelRequests = 0,
    cancelResponses = 0;
  const cancelGates: (() => void)[] = [];
  const posts: any[] = [],
    runs = new Map<string, any>(),
    gates: (() => void)[] = [];
  const evidence = {
    id: "risk-asset-0:rows-0",
    asset_id: "risk-asset-0",
    domain_id: "risk",
    name: "Counterparty exposure",
    text: "Aster Capital has USD 1,250,000 in synthetic exposure.",
    provenance: {
      type: "structured",
      location: "postgresql://atlas/risk/counterparty_exposure",
      row_id: "CP-1000",
    },
  };
  const product = (finance = false, legal = false): DiscoveryItem => ({
    id: legal
      ? "legal-product-0"
      : finance
        ? "finance-product-0"
        : "risk-product-0",
    kind: "product",
    title: legal
      ? "Contract Obligations"
      : finance
        ? "Treasury Liquidity"
        : "Counterparty Risk Intelligence",
    excerpt: "Governed synthetic knowledge and supporting sources.",
    domain_id: legal ? "legal" : finance ? "finance" : "risk",
    source_type: "Knowledge product",
    asset_id: null,
    product_id: legal
      ? "legal-product-0"
      : finance
        ? "finance-product-0"
        : "risk-product-0",
    evidence_id: null,
    steward: "Priya Shah",
    quality: 97,
    score: 0.03,
  });
  await page.route("**/api/discovery/search?**", async (route) => {
    const url = new URL(route.request().url()),
      q = url.searchParams.get("q") || "";
    if (options.failResults) {
      await route.fulfill({
        status: 503,
        json: { detail: "Search index unavailable" },
      });
      return;
    }
    if (options.delayResults && q.includes("counterparty"))
      await new Promise((resolve) => setTimeout(resolve, 4000));
    const legal = route
      .request()
      .headers()
      ["authorization"]?.endsWith("-legal");
    const doc: DiscoveryItem = {
      ...product(),
      id: "risk-asset-1",
      kind: "document",
      title: "Counterparty due diligence policy",
      source_type: "MinIO",
      product_id: null,
      asset_id: "risk-asset-1",
      evidence_id: "risk-asset-1:chunk-0",
    };
    let items: DiscoveryItem[] = [product(q.includes("treasury"), legal), doc];
    const type = url.searchParams.get("type");
    if (type && type !== "all") items = items.filter((i) => i.kind === type);
    if (url.searchParams.get("page") === "2")
      items = [
        {
          ...doc,
          id: "risk-asset-3",
          title: "Due diligence control guide",
          asset_id: "risk-asset-3",
          evidence_id: null,
        },
      ];
    await route
      .fulfill({
        json: {
          items,
          returned_count: items.length,
          has_more: url.searchParams.get("page") !== "2",
          page: Number(url.searchParams.get("page") || 1),
          page_size: 20,
          query: q,
          domain_id: url.searchParams.get("domain_id"),
        },
      })
      .catch(() => {});
  });
  await page.route("**/api/search/runs", async (route) => {
    const input = route.request().postDataJSON();
    posts.push(input);
    const id = "mock-" + posts.length;
    const run = {
      run_id: id,
      query: input.query,
      domain_id: input.domain_id || null,
      mode: input.mode,
      status: options.failAI ? "failed" : "running",
      statements: [],
      evidence: [],
      gaps: [],
      events: [
        {
          sequence: 1,
          stage: "retrieve",
          status: "running",
          summary: "Searching authorized sources",
          at: Date.now() / 1000,
        },
      ],
      graph: {
        nodes: [
          {
            id: "Counterparty",
            name: "Counterparty",
            iri: "urn:Counterparty",
            kind: "concept",
          },
          {
            id: "Exposure",
            name: "Exposure",
            iri: "urn:Exposure",
            kind: "concept",
          },
        ],
        edges: [
          { source: "Counterparty", target: "Exposure", label: "has exposure" },
        ],
      },
      created_at: Date.now() / 1000,
      error: options.failAI ? "Provider unavailable" : undefined,
    };
    runs.set(id, run);
    await route.fulfill({ json: run });
  });
  await page.route("**/api/search/runs/**", async (route) => {
    const parts = new URL(route.request().url()).pathname.split("/"),
      id = parts[4],
      run = runs.get(id);
    if (parts[5] === "cancel") {
      run.status = "cancelled";
      cancelRequests++;
      if (options.delayCancel)
        await new Promise<void>((resolve) => cancelGates.push(resolve));
      await route.fulfill({ json: run });
      cancelResponses++;
      return;
    }
    if (parts[5] === "events") {
      if (options.delayAI && !released)
        await new Promise<void>((resolve) => gates.push(resolve));
      if (run.status === "running")
        Object.assign(run, {
          status: "completed",
          statements: [
            {
              text: run.query.includes("treasury")
                ? "Fresh treasury answer"
                : "Fresh counterparty answer",
              evidence_ids: [evidence.id],
              support_status: "supported",
              supporting_locators: [
                {
                  evidence_id: evidence.id,
                  source_title: "Counterparty exposure",
                  source_ref: { locator: "row:CP-1000" },
                  field: "exposure",
                  value: 1250000,
                  unit: "USD",
                },
              ],
            },
          ],
          answer_sections: [{ title: "Answer", statement_indices: [0] }],
          evidence: [evidence],
          events: [
            ...run.events,
            {
              sequence: 2,
              stage: "finish",
              status: "completed",
              summary: "Search completed",
              at: Date.now() / 1000,
            },
          ],
        });
      await route
        .fulfill({
          contentType: "text/event-stream",
          body: "event: result\ndata: " + JSON.stringify(run) + "\n\n",
        })
        .catch(() => {});
      return;
    }
    await route.fulfill({ json: run });
  });
  await page.route("**/api/evidence/**", (route) =>
    route.fulfill({ json: evidence }),
  );
  return {
    posts,
    cancelRequests: () => cancelRequests,
    completedCancels: () => cancelResponses,
    releaseCancels: () => cancelGates.splice(0).forEach((resolve) => resolve()),
    release: () => {
      released = true;
      gates.splice(0).forEach((resolve) => resolve());
    },
  };
}
async function submit(page: Page, query = "counterparty exposure") {
  await page.goto("/");
  await page
    .getByRole("searchbox", { name: "Search enterprise knowledge" })
    .fill(query);
  await page
    .getByRole("button", { name: "Search knowledge", exact: true })
    .click();
  await expect(page).toHaveURL(/\/search\?q=/);
}

test("results arrive while one cited answer builds and browsing does not regenerate it", async ({
  page,
}) => {
  const boundary = await boundaries(page, { delayAI: true });
  try {
    await submit(page);
    await expect(
      page.getByRole("button", {
        name: "Counterparty Risk Intelligence",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByText("Finding a cited answer…", { exact: true }),
    ).toBeVisible();
    expect(boundary.posts).toHaveLength(1);
    boundary.release();
    await expect(
      page.getByRole("heading", { name: "Answer", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".answer-citations")).not.toContainText(
      "Source 1",
    );
    await expect(
      page.getByText("Fresh counterparty answer", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", {
        name: "Open source: Counterparty exposure · row:CP-1000",
        exact: true,
      })
      .click();
    await expect(page.getByRole("dialog")).toContainText("USD 1,250,000");
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Documents", exact: true }).click();
    await page.getByLabel("Sort results").selectOption("name");
    await page
      .getByRole("button", { name: "Next results", exact: true })
      .click();
    await expect(
      page.getByRole("button", {
        name: "Due diligence control guide",
        exact: true,
      }),
    ).toBeVisible();
    await page.goBack();
    await page.reload();
    await expect(
      page.getByText("Fresh counterparty answer", { exact: true }),
    ).toBeVisible();
    expect(boundary.posts).toHaveLength(1);
  } finally {
    boundary.release();
  }
});

test("AI failure leaves useful discovery results", async ({ page }) => {
  const boundary = await boundaries(page, { failAI: true });
  await submit(page);
  await expect(
    page.getByText("Provider unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    }),
  ).toBeVisible();
  expect(boundary.posts).toHaveLength(1);
});

test("result failure does not hide a valid cited answer", async ({ page }) => {
  await boundaries(page, { failResults: true });
  await submit(page);
  await expect(
    page.getByText("Fresh counterparty answer", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Search index unavailable", { exact: true }),
  ).toBeVisible();
});

test("new queries reject late results and cancel superseded answers", async ({
  page,
}) => {
  const boundary = await boundaries(page, {
    delayAI: true,
    delayResults: true,
  });
  try {
    await submit(page);
    await expect.poll(() => boundary.posts.length).toBe(1);
    await page
      .getByRole("searchbox", { name: "Search enterprise knowledge" })
      .fill("treasury liquidity");
    await page
      .getByRole("button", { name: "Search knowledge", exact: true })
      .click();
    await expect.poll(() => boundary.posts.length).toBe(2);
    await expect(
      page.getByRole("button", { name: "Treasury Liquidity", exact: true }),
    ).toBeVisible();
    boundary.release();
    await expect(
      page.getByText("Fresh treasury answer", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Fresh counterparty answer", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", {
        name: "Counterparty Risk Intelligence",
        exact: true,
      }),
    ).toHaveCount(0);
  } finally {
    boundary.release();
  }
});

test("domain submission scopes both result and AI requests", async ({
  page,
}) => {
  const boundary = await boundaries(page);
  await submit(page, "treasury liquidity");
  await expect(
    page.getByText("Fresh treasury answer", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Search domain").selectOption("finance");
  await page
    .getByRole("button", { name: "Search knowledge", exact: true })
    .click();
  await expect.poll(() => boundary.posts.length).toBe(2);
  expect(boundary.posts[1].domain_id).toBe("finance");
  await expect(page).toHaveURL(/domain_id=finance/);
  await expect(
    page.getByText("Fresh treasury answer", { exact: true }),
  ).toBeVisible();
});

test("cancelled answers stay cancelled across reload without another provider call", async ({
  page,
}) => {
  const boundary = await boundaries(page, { delayAI: true });
  try {
    await submit(page);
    await expect(
      page.getByRole("button", { name: "Stop answer", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Stop answer", exact: true })
      .click();
    await expect(
      page.getByText("Answer cancelled", { exact: true }),
    ).toBeVisible();
    boundary.release();
    await page.reload();
    await expect(
      page.getByText("Answer cancelled", { exact: true }),
    ).toBeVisible();
    expect(boundary.posts).toHaveLength(1);
  } finally {
    boundary.release();
  }
});

test("changing persona clears previous access-scoped results", async ({
  page,
}) => {
  const boundary = await boundaries(page);
  await submit(page);
  await expect(
    page.getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("Demo persona").selectOption("legal");
  await expect(
    page.getByRole("button", { name: "Contract Obligations", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Fresh counterparty answer", { exact: true }),
  ).toHaveCount(0);
  expect(boundary.posts).toHaveLength(1);
});

test("a late cancellation response cannot replace a newer answer", async ({
  page,
}) => {
  const boundary = await boundaries(page, { delayAI: true, delayCancel: true });
  try {
    await submit(page);
    await expect(
      page.getByRole("button", { name: "Stop answer", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Stop answer", exact: true })
      .click();
    await expect.poll(boundary.cancelRequests).toBe(1);
    await page
      .getByRole("searchbox", { name: "Search enterprise knowledge" })
      .fill("treasury liquidity");
    await page
      .getByRole("button", { name: "Search knowledge", exact: true })
      .click();
    await expect.poll(() => boundary.posts.length).toBe(2);
    boundary.release();
    await expect(
      page.getByText("Fresh treasury answer", { exact: true }),
    ).toBeVisible();
    boundary.releaseCancels();
    await expect.poll(boundary.completedCancels).toBe(1);
    await expect(
      page.getByText("Fresh treasury answer", { exact: true }),
    ).toBeVisible();
  } finally {
    boundary.release();
    boundary.releaseCancels();
  }
});

test("duplicate header submits start one provider request", async ({
  page,
}) => {
  const boundary = await boundaries(page);
  await page.goto("/search?q=counterparty+exposure");
  await expect(
    page.getByRole("button", {
      name: "Counterparty Risk Intelligence",
      exact: true,
    }),
  ).toBeVisible();
  expect(boundary.posts).toHaveLength(0);
  await page
    .getByRole("button", { name: "Search knowledge", exact: true })
    .dblclick();
  await expect(
    page.getByText("Fresh counterparty answer", { exact: true }),
  ).toBeVisible();
  expect(boundary.posts).toHaveLength(1);
});

test("a reconnected pending answer is cancelled when another query replaces it", async ({
  page,
}) => {
  const boundary = await boundaries(page, { delayAI: true });
  try {
    await submit(page);
    await expect.poll(() => boundary.posts.length).toBe(1);
    await expect(
      page.getByRole("button", { name: "Stop answer", exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("button", { name: "Stop answer", exact: true }),
    ).toBeVisible();
    await page.getByRole("searchbox").fill("treasury liquidity");
    await page
      .getByRole("button", { name: "Search knowledge", exact: true })
      .click();
    await expect.poll(boundary.cancelRequests).toBe(1);
    await expect.poll(() => boundary.posts.length).toBe(2);
  } finally {
    boundary.release();
  }
});

test("mobile answers retain their ontology relationships", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const boundary = await boundaries(page);
  await submit(page);
  await expect(
    page.getByText("Fresh counterparty answer", { exact: true }),
  ).toBeVisible();
  await page.getByText("Ontology context", { exact: true }).click();
  await expect(page.getByText("has exposure", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Explore relationships" }),
  ).toBeVisible();
  boundary.release();
});

test("a completed ambiguity asks the clarification question without regenerating", async ({
  page,
}) => {
  await boundaries(page);
  let generations = 0;
  await page.route("**/api/search/runs", (route) => {
    generations++;
    return route.fulfill({
      json: {
        run_id: "ambiguous-demo",
        query: "Which policy?",
        status: "completed",
        mode: "llm",
        answer_outcome: "needs_clarification",
        clarification:
          "Which position and domain do you mean: Finance or People?",
        statements: [],
        evidence: [],
        gaps: [],
        events: [],
        graph: { nodes: [], edges: [] },
      },
    });
  });
  await page.goto("/");
  await page
    .getByRole("searchbox", { name: "Search enterprise knowledge" })
    .fill("Which policy?");
  await page
    .getByRole("searchbox", { name: "Search enterprise knowledge" })
    .press("Enter");
  await expect(
    page.getByRole("heading", { name: "Clarify your question", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Which position and domain do you mean: Finance or People?",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Refine search", exact: true })
    .click();
  await expect(
    page.getByRole("searchbox", { name: "Search enterprise knowledge" }),
  ).toBeFocused();
  expect(generations).toBe(1);
});
