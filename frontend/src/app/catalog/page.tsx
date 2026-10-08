"use client";
import { motion } from "framer-motion";
import { Suspense, useCallback, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Grid2X2, List, ArrowUpRight } from "lucide-react";
import { useData, RecordItem, CatalogPage } from "@/api/client";
import { useSession } from "@/components/Shell";
import { Loading, Formats, Quality, DomainName } from "@/components/Common";
import SearchBox from "@/components/discovery/SearchBox";
import DiscoveryDetail from "@/components/discovery/DiscoveryDetail";
import { prepareSearch } from "@/api/discovery";
function Library() {
  const params = useSearchParams();
  const router = useRouter();
  const { token, persona } = useSession();
  const [advanced, setAdvanced] = useState(false);
  const domain = params.get("domain_id") || "";
  const kind = params.get("kind") === "asset" ? "asset" : "product";
  const view = params.get("view") === "list" ? "list" : "grid";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const selected = params.get("selected");
  function update(values: Record<string, string>, reset = true) {
    const next = new URLSearchParams(params.toString());
    if (reset) {
      next.delete("page");
      next.delete("selected");
    }
    for (const [key, value] of Object.entries(values))
      value ? next.set(key, value) : next.delete(key);
    window.history.pushState(
      null,
      "",
      "/catalog" + (next.size ? "?" + next : ""),
    );
  }
  const close = useCallback(() => {
    const next = new URLSearchParams(window.location.search);
    next.delete("selected");
    window.history.replaceState(
      null,
      "",
      "/catalog" + (next.size ? "?" + next : ""),
    );
  }, []);
  const query = new URLSearchParams({
    kind,
    page: String(page),
    page_size: "12",
    sort: params.get("sort") || "name",
  });
  for (const key of [
    "domain_id",
    "source_id",
    "quality",
    "text",
    "subdomain_id",
    "owner_id",
    "status",
    "classification",
    "asset_type",
  ]) {
    if (params.get(key)) query.set(key, params.get(key)!);
  }
  const records = useData<CatalogPage>("/catalog?" + query, token);
  const domains = useData<RecordItem[]>("/domains", token);
  const sources = useData<CatalogPage>(
    "/catalog?kind=source&page_size=100",
    token,
  );
  function select(
    key: string,
    label: string,
    options: { id: string; name: string }[],
  ) {
    return (
      <label className="library-filter">
        {label}
        <select
          aria-label={"Filter by " + label.toLowerCase()}
          value={params.get(key) || ""}
          onChange={(e) =>
            update({
              [key]: e.target.value,
              ...(key === "domain_id"
                ? { source_id: "", subdomain_id: "" }
                : {}),
            })
          }
        >
          <option value="">
            {label === "Quality"
              ? "All quality states"
              : "All " + label.toLowerCase() + "s"}
          </option>
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      </label>
    );
  }
  return (
    <div className="library-page">
      <div className="library-heading">
        <span className="eyebrow">EXPLORE THE ENTERPRISE</span>
        <h1>Knowledge catalog</h1>
        <p>
          Find a product. Understand its sources. Put trusted knowledge to work.
        </p>
      </div>
      <SearchBox
        compact
        domainId={domain || null}
        showDomainSelector={false}
        onSubmit={(value) => router.push(prepareSearch(value, persona))}
      />
      <div className="library-filters">
        {select("domain_id", "Domain", domains.data || [])}
        {select(
          "source_id",
          "Source",
          sources.data?.items.filter(
            (s) => !domain || s.domain_id === domain,
          ) || [],
        )}
        {select("quality", "Quality", [
          { id: "healthy", name: "Healthy · 90%+" },
          { id: "attention", name: "Needs attention" },
        ])}
        <button
          className="btn btn-ghost"
          aria-expanded={advanced}
          onClick={() => setAdvanced(!advanced)}
        >
          More filters
        </button>
      </div>
      {advanced && (
        <motion.div
          className="library-filters advanced-filters"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.16 }}
        >
          <label className="library-filter">
            Name or tag
            <input
              aria-label="Filter by name or tag"
              value={params.get("text") || ""}
              onChange={(e) => update({ text: e.target.value })}
            />
          </label>
          {select(
            "subdomain_id",
            "Subdomain",
            domains.data
              ?.filter((d) => !domain || d.id === domain)
              .flatMap((d) => d.subdomains || []) || [],
          )}
          {select(
            "owner_id",
            "Steward",
            domains.data?.map((d) => ({
              id: d.steward || "",
              name: d.steward || "",
            })) || [],
          )}
          {select(
            "status",
            "Status",
            ["Active", "Draft", "In development"].map((id) => ({
              id,
              name: id,
            })),
          )}
          {select(
            "classification",
            "Classification",
            ["Internal", "Confidential"].map((id) => ({ id, name: id })),
          )}
          {kind === "asset" &&
            select(
              "asset_type",
              "Asset type",
              ["Table", "Document", "Metadata", "Data product"].map((id) => ({
                id,
                name: id,
              })),
            )}
        </motion.div>
      )}
      <div className="library-toolbar">
        <div className="segmented">
          {["product", "asset"].map((k) => (
            <button
              key={k}
              className={kind === k ? "active" : ""}
              aria-pressed={kind === k}
              onClick={() =>
                update({ kind: k === "product" ? "" : k, asset_type: "" })
              }
            >
              {k === "product" ? "Products" : "Assets"}
            </button>
          ))}
        </div>
        <span className="library-count">
          {records.data
            ? `${records.data.total} ${kind === "product" ? "products" : "assets"}`
            : "Loading catalog"}
        </span>
        <div className="library-view">
          <select
            aria-label="Sort catalog"
            value={params.get("sort") || "name"}
            onChange={(e) => update({ sort: e.target.value })}
          >
            <option value="name">Name A–Z</option>
            <option value="updated">Recently updated</option>
            <option value="quality">Lowest quality first</option>
          </select>
          {["grid", "list"].map((v) => (
            <button
              key={v}
              className="icon-button"
              aria-label={v === "grid" ? "Grid view" : "List view"}
              aria-pressed={view === v}
              onClick={() => update({ view: v === "grid" ? "" : v }, false)}
            >
              {v === "grid" ? <Grid2X2 size={18} /> : <List size={18} />}
            </button>
          ))}
        </div>
      </div>
      {records.loading || records.error ? (
        <Loading error={records.error} />
      ) : !records.data?.items.length ? (
        <>
          <Loading loading={false} />
          <button
            className="btn btn-secondary"
            onClick={() => router.push("/catalog")}
          >
            Clear filters
          </button>
        </>
      ) : (
        <div className={"library-records " + view}>
          {records.data.items.map((item) => (
            <button
              key={item.id}
              className="library-record"
              aria-label={item.name}
              onClick={() => update({ selected: item.id }, false)}
            >
              <div className="library-record-domain">
                <DomainName id={item.domain_id} />
                <ArrowUpRight size={16} />
              </div>
              <h2>{item.name}</h2>
              <p>{item.description}</p>
              <Formats
                items={
                  kind === "product"
                    ? item.formats
                    : [
                        item.type === "Document"
                          ? "Document"
                          : item.type === "Metadata"
                            ? "RDF"
                            : "SQL",
                        "Vector",
                      ]
                }
              />
              <div className="library-record-footer">
                <span>{item.steward}</span>
                {item.quality != null && <Quality value={item.quality} />}
              </div>
            </button>
          ))}
        </div>
      )}
      {records.data && records.data.total > 0 && (
        <div className="pagination">
          <span>
            Showing {(page - 1) * 12 + 1}–
            {Math.min(page * 12, records.data.total)} of {records.data.total}
          </span>
          <div className="actions-row">
            <button
              className="btn btn-secondary"
              disabled={page === 1}
              onClick={() => update({ page: String(page - 1) }, false)}
            >
              Previous
            </button>
            <button
              className="btn btn-secondary"
              disabled={page * 12 >= records.data.total}
              onClick={() => update({ page: String(page + 1) }, false)}
            >
              Next
            </button>
          </div>
        </div>
      )}
      {selected && (
        <DiscoveryDetail
          key={token + selected}
          id={selected}
          kind={kind}
          onClose={close}
        />
      )}
    </div>
  );
}
export default function Catalog() {
  return (
    <Suspense fallback={<Loading />}>
      <Library />
    </Suspense>
  );
}
