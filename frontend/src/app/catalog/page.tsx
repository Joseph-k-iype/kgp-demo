"use client";
import Link from "next/link";
import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Search,
  Layers,
  Database,
  Box,
  ShieldCheck,
  ArrowUpRight,
  ChevronRight,
  User,
  Network,
  FileText,
  ArrowRight,
} from "lucide-react";
import { useData, RecordItem, CatalogPage } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  PageHeading,
  Badge,
  Loading,
  AssetIcon,
  Formats,
  Quality,
  DomainName,
  DetailGrid,
} from "@/components/Common";
import AssetDetail from "@/components/AssetDetail";
function CatalogContent() {
  const queryString = useSearchParams().toString();
  const router = useRouter();
  const lastWritten = useRef<string | null>(null);
  const { token } = useSession();
  const [domain, setDomain] = useState(""),
    [text, setText] = useState(""),
    [kind, setKind] = useState("product"),
    [source, setSource] = useState(""),
    [quality, setQuality] = useState(""),
    [sort, setSort] = useState("name"),
    [page, setPage] = useState(1),
    [selected, setSelected] = useState(""),
    [asset, setAsset] = useState(""),
    [ready, setReady] = useState(false),
    [advanced, setAdvanced] = useState(false),
    [subdomain, setSubdomain] = useState(""),
    [owner, setOwner] = useState(""),
    [status, setStatus] = useState(""),
    [classification, setClassification] = useState(""),
    [assetType, setAssetType] = useState("");
  useEffect(() => {
    if (lastWritten.current === queryString) return;
    const params = new URLSearchParams(queryString);
    setDomain(params.get("domain_id") || "");
    setText(params.get("text") || "");
    setKind(params.get("kind") || "product");
    setSource(params.get("source_id") || "");
    setQuality(params.get("quality") || "");
    setSort(params.get("sort") || "name");
    setPage(Number(params.get("page") || 1));
    setSubdomain(params.get("subdomain_id") || "");
    setOwner(params.get("owner_id") || "");
    setStatus(params.get("status") || "");
    setClassification(params.get("classification") || "");
    setAssetType(params.get("asset_type") || "");
    setAdvanced(
      [
        "subdomain_id",
        "owner_id",
        "status",
        "classification",
        "asset_type",
      ].some((k) => params.has(k)),
    );
    setSelected(params.get("selected") || "");
    setReady(true);
  }, [queryString]);
  useEffect(() => {
    if (!ready) return;
    const p = new URLSearchParams();
    if (domain) p.set("domain_id", domain);
    if (text) p.set("text", text);
    if (kind !== "product") p.set("kind", kind);
    if (selected) p.set("selected", selected);
    if (source) p.set("source_id", source);
    if (quality) p.set("quality", quality);
    if (sort !== "name") p.set("sort", sort);
    if (page > 1) p.set("page", String(page));
    if (subdomain) p.set("subdomain_id", subdomain);
    if (owner) p.set("owner_id", owner);
    if (status) p.set("status", status);
    if (classification) p.set("classification", classification);
    if (assetType) p.set("asset_type", assetType);
    lastWritten.current = p.toString();
    if (p.toString() === queryString) return;
    router.replace("/catalog" + (p.size ? "?" + p.toString() : ""), {
      scroll: false,
    });
  }, [
    domain,
    text,
    kind,
    selected,
    ready,
    source,
    quality,
    sort,
    page,
    subdomain,
    owner,
    status,
    classification,
    assetType,
  ]);
  const query = new URLSearchParams({
    kind,
    text,
    sort,
    page: String(page),
    page_size: "8",
    ...(domain ? { domain_id: domain } : {}),
    ...(source ? { source_id: source } : {}),
    ...(quality ? { quality } : {}),
    ...(subdomain ? { subdomain_id: subdomain } : {}),
    ...(owner ? { owner_id: owner } : {}),
    ...(status ? { status } : {}),
    ...(classification ? { classification } : {}),
    ...(assetType ? { asset_type: assetType } : {}),
  });
  const list = useData<CatalogPage>(ready ? "/catalog?" + query : null, token),
    domains = useData<RecordItem[]>("/domains", token),
    sources = useData<CatalogPage>("/catalog?kind=source&page_size=100", token),
    overview = useData<{ counts: Record<string, number> }>("/overview", token);
  const effectiveSelected = selected || list.data?.items[0]?.id || "";
  const detail = useData<RecordItem>(
    effectiveSelected && kind === "product"
      ? "/products/" + effectiveSelected
      : null,
    token,
  );
  function changeFilter(fn: () => void) {
    fn();
    setPage(1);
    setSelected("");
  }
  return (
    <>
      <PageHeading
        title="Knowledge catalog"
        description="Discover trusted products, explore their sources, and connect knowledge across the enterprise."
        action={
          <Link className="btn btn-secondary" href="/search">
            <Search size={14} /> Ask knowledge <ArrowUpRight size={13} />
          </Link>
        }
      />
      <div className="stats">
        {[
          ["Knowledge products", overview.data?.counts.product, Box],
          ["Business domains", overview.data?.counts.domain, Layers],
          ["Underlying assets", overview.data?.counts.asset, Database],
          ["Governed sources", overview.data?.counts.source, ShieldCheck],
        ].map(([label, value, Icon]) => {
          const I = Icon as typeof Box;
          return (
            <div className="stat" key={String(label)}>
              <span className="stat-icon">
                <I size={21} />
              </span>
              <div>
                <div className="stat-label">{String(label)}</div>
                <div className="stat-value">
                  {typeof value === "number" ? value : "—"}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="catalog-layout">
        <section>
          <div className="filterbar">
            <div className="filter-field">
              <label htmlFor="domain-filter">Domain</label>
              <select
                id="domain-filter"
                aria-label="Filter by domain"
                value={domain}
                onChange={(e) =>
                  changeFilter(() => {
                    setDomain(e.target.value);
                    setSource("");
                    setSubdomain("");
                  })
                }
              >
                <option value="">All domains</option>
                {domains.data?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="filter-field">
              <label htmlFor="source-filter">Source</label>
              <select
                id="source-filter"
                aria-label="Filter by source"
                value={source}
                onChange={(e) => changeFilter(() => setSource(e.target.value))}
              >
                <option value="">All sources</option>
                {sources.data?.items
                  .filter((s) => !domain || s.domain_id === domain)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
              </select>
            </div>
            <div className="filter-field">
              <label htmlFor="quality-filter">Quality</label>
              <select
                id="quality-filter"
                aria-label="Filter by quality"
                value={quality}
                onChange={(e) => changeFilter(() => setQuality(e.target.value))}
              >
                <option value="">All quality states</option>
                <option value="healthy">Healthy · 90%+</option>
                <option value="attention">Needs attention</option>
              </select>
            </div>
            <div className="filter-field search-field">
              <label htmlFor="catalog-search">Find knowledge</label>
              <div className="search-input">
                <Search size={14} />
                <input
                  id="catalog-search"
                  placeholder="Search name, description, tags…"
                  value={text}
                  onChange={(e) => changeFilter(() => setText(e.target.value))}
                />
              </div>
            </div>
          </div>
          <button
            className="btn btn-ghost"
            style={{ marginBottom: 12 }}
            onClick={() => setAdvanced(!advanced)}
          >
            {advanced ? "Hide advanced filters" : "Advanced filters"}
          </button>
          {advanced && (
            <div className="filterbar">
              <div className="filter-field">
                <label>Subdomain</label>
                <select
                  aria-label="Filter by subdomain"
                  value={subdomain}
                  onChange={(e) =>
                    changeFilter(() => setSubdomain(e.target.value))
                  }
                >
                  <option value="">All subdomains</option>
                  {domains.data
                    ?.filter((d) => !domain || d.id === domain)
                    .flatMap((d) => d.subdomains || [])
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                </select>
              </div>
              <div className="filter-field">
                <label>Steward</label>
                <select
                  aria-label="Filter by steward"
                  value={owner}
                  onChange={(e) => changeFilter(() => setOwner(e.target.value))}
                >
                  <option value="">All stewards</option>
                  {domains.data?.map((d) => (
                    <option key={d.id} value={d.steward}>
                      {d.steward}
                    </option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>Status</label>
                <select
                  aria-label="Filter by status"
                  value={status}
                  onChange={(e) =>
                    changeFilter(() => setStatus(e.target.value))
                  }
                >
                  <option value="">All statuses</option>
                  {["Active", "Draft", "In development"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>Classification</label>
                <select
                  aria-label="Filter by classification"
                  value={classification}
                  onChange={(e) =>
                    changeFilter(() => setClassification(e.target.value))
                  }
                >
                  <option value="">All classifications</option>
                  <option>Internal</option>
                  <option>Confidential</option>
                </select>
              </div>
              {kind === "asset" && (
                <div className="filter-field">
                  <label>Asset type</label>
                  <select
                    aria-label="Filter by asset type"
                    value={assetType}
                    onChange={(e) =>
                      changeFilter(() => setAssetType(e.target.value))
                    }
                  >
                    <option value="">All asset types</option>
                    {["Table", "Document", "Metadata", "Data product"].map(
                      (t) => (
                        <option key={t}>{t}</option>
                      ),
                    )}
                  </select>
                </div>
              )}
            </div>
          )}
          <div className="catalog-toolbar">
            <span>
              {list.data
                ? `${list.data.total} ${kind === "product" ? "products" : "assets"}`
                : "Loading catalog"}
            </span>
            <div className="actions-row">
              <div className="segmented">
                <button
                  className={kind === "product" ? "active" : ""}
                  onClick={() =>
                    changeFilter(() => {
                      setKind("product");
                      setAssetType("");
                    })
                  }
                >
                  Products
                </button>
                <button
                  className={kind === "asset" ? "active" : ""}
                  onClick={() => changeFilter(() => setKind("asset"))}
                >
                  Assets
                </button>
              </div>
              <select
                aria-label="Sort catalog"
                style={{ fontSize: 10, padding: "5px 8px" }}
                value={sort}
                onChange={(e) => setSort(e.target.value)}
              >
                <option value="name">Name A–Z</option>
                <option value="updated">Recently updated</option>
                <option value="quality">Quality</option>
              </select>
            </div>
          </div>
          {list.loading || list.error ? (
            <div className="panel">
              <Loading error={list.error} />
            </div>
          ) : !list.data?.items.length ? (
            <div className="panel">
              <Loading loading={false} />
              <button
                className="btn btn-secondary"
                style={{ margin: "0 auto 20px", display: "flex" }}
                onClick={() =>
                  changeFilter(() => {
                    setDomain("");
                    setText("");
                    setSource("");
                    setQuality("");
                    setSubdomain("");
                    setOwner("");
                    setStatus("");
                    setClassification("");
                    setAssetType("");
                  })
                }
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div className="record-list">
              {list.data.items.map((r) => (
                <button
                  key={r.id}
                  className={
                    "record-row " +
                    (effectiveSelected === r.id ? "selected" : "")
                  }
                  onClick={() =>
                    kind === "asset" ? setAsset(r.id) : setSelected(r.id)
                  }
                  aria-label={r.name}
                >
                  <AssetIcon type={r.type} />
                  <div className="record-main">
                    <div className="record-top">
                      <h3>{r.name}</h3>
                      <Quality value={r.quality} />
                    </div>
                    <p>{r.description}</p>
                    <Formats
                      items={
                        kind === "product"
                          ? r.formats
                          : [
                              r.type === "Document"
                                ? "Document"
                                : r.type === "Metadata"
                                  ? "RDF"
                                  : "SQL",
                              "Vector",
                            ]
                      }
                    />
                    <div className="record-meta">
                      <span>
                        <Layers size={11} />
                        <DomainName id={r.domain_id} />
                      </span>
                      <span>
                        <User size={11} />
                        {r.steward}
                      </span>
                      <span>
                        {kind === "product"
                          ? `${r.asset_count} assets`
                          : r.indexing_state === "ready"
                            ? "Indexed"
                            : "Index pending"}
                      </span>
                    </div>
                  </div>
                  <ChevronRight
                    size={14}
                    style={{ marginTop: 6, color: "#9aadc4" }}
                  />
                </button>
              ))}
            </div>
          )}
          {list.data && (
            <div className="pagination">
              <span>
                Showing {(page - 1) * 8 + 1}–
                {Math.min(page * 8, list.data.total)} of {list.data.total}
              </span>
              <div className="actions-row">
                <button
                  className="btn btn-secondary"
                  disabled={page === 1}
                  onClick={() => setPage((n) => n - 1)}
                >
                  Previous
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={page * 8 >= list.data.total}
                  onClick={() => setPage((n) => n + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </section>
        <aside className="panel detail-panel">
          {kind === "asset" ? (
            <div className="empty-detail">
              <Database size={26} />
              <h2 style={{ margin: "14px 0 8px" }}>
                Inspect an underlying asset
              </h2>
              <p>
                Select an asset to explore its source, schema, evidence and
                ontology.
              </p>
            </div>
          ) : detail.loading && effectiveSelected ? (
            <Loading />
          ) : detail.error ? (
            <Loading error={detail.error} />
          ) : detail.data ? (
            <>
              <div className="detail-header">
                <div className="detail-header-top">
                  <AssetIcon />
                  <h2>{detail.data.name}</h2>
                </div>
                <p>{detail.data.description}</p>
                <Formats items={detail.data.formats} />
              </div>
              <div className="detail-section">
                <h3>
                  Overview{" "}
                  <Badge
                    tone={detail.data.status === "Active" ? "teal" : "neutral"}
                  >
                    {detail.data.status}
                  </Badge>
                </h3>
                <DetailGrid record={detail.data} />
              </div>
              <div className="detail-section">
                <h3>
                  Underlying sources{" "}
                  <span className="muted">
                    {detail.data.assets?.length} assets
                  </span>
                </h3>
                <div className="storage-source">
                  <span className="mini-icon">
                    <img
                      src="/design/postgres.png"
                      alt=""
                      width={21}
                      height={23}
                    />
                  </span>
                  <div>
                    PostgreSQL
                    <small>Structured records · System of record</small>
                  </div>
                </div>
                <div className="storage-source">
                  <span className="mini-icon">
                    <img
                      src="/design/minio.png"
                      alt=""
                      width={14}
                      height={23}
                    />
                  </span>
                  <div>
                    MinIO object store
                    <small>Documents · Supporting evidence</small>
                  </div>
                </div>
                {detail.data.assets?.map((a) => (
                  <button
                    key={a.id}
                    className="asset-link"
                    onClick={() => setAsset(a.id)}
                    aria-label={a.name}
                  >
                    {a.type === "Document" ? (
                      <FileText size={13} />
                    ) : (
                      <Database size={13} />
                    )}
                    <span>{a.name}</span>
                    <ChevronRight size={12} />
                  </button>
                ))}
              </div>
              <div className="detail-section">
                <h3>
                  Ontology relationships{" "}
                  <Link
                    className="text-link"
                    href={"/ontology?concept=" + detail.data.concepts?.[0]}
                  >
                    Explore <ArrowUpRight size={11} />
                  </Link>
                </h3>
                <div className="concepts">
                  {detail.data.concepts?.map((c) => (
                    <Link
                      key={c}
                      href={"/ontology?concept=" + c}
                      className="concept-chip"
                    >
                      <Network size={11} />
                      {c}
                    </Link>
                  ))}
                </div>
                <div
                  className="small-text muted"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 7,
                    marginTop: 14,
                  }}
                >
                  Source <ArrowRight size={12} /> Asset <ArrowRight size={12} />{" "}
                  Knowledge product
                </div>
              </div>
              <div className="detail-section">
                <h3>
                  Knowledge quality <Quality value={detail.data.quality} />
                </h3>
                <div className="quality-bar">
                  <span style={{ width: detail.data.quality + "%" }} />
                </div>
                <p className="metric-note">
                  Synthetic quality score · See asset issues for evidence
                </p>
                {detail.data.gaps?.length ? (
                  <Link
                    href="/projects"
                    className="notice amber"
                    style={{ display: "block", marginTop: 13 }}
                  >
                    {detail.data.gaps.length} coverage gap requires attention{" "}
                    <ArrowUpRight size={12} />
                  </Link>
                ) : null}
              </div>
              <div className="detail-section">
                <h3>Tags</h3>
                <div className="concepts">
                  {detail.data.tags?.map((t) => (
                    <Badge key={t} tone="neutral">
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-detail">
              Select a knowledge product to inspect its sources.
            </div>
          )}
        </aside>
      </div>
      {asset && <AssetDetail id={asset} onClose={() => setAsset("")} />}
    </>
  );
}

export default function Catalog() {
  return (
    <Suspense fallback={<Loading />}>
      <CatalogContent />
    </Suspense>
  );
}
