"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { Suspense, useCallback, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Layers,
  Box,
  Database,
  FileText,
  ArrowRight,
  ShieldCheck,
  ChevronDown,
} from "lucide-react";
import { useSession } from "@/components/Shell";
import { Loading, DomainName } from "@/components/Common";
import SearchBox from "@/components/discovery/SearchBox";
import SearchHeader from "@/components/discovery/SearchHeader";
import AnswerPanel from "@/components/discovery/AnswerPanel";
import ResultList from "@/components/discovery/ResultList";
import DiscoveryDetail, {
  EvidenceDetail,
} from "@/components/discovery/DiscoveryDetail";
import { DiscoveryItem, prepareSearch } from "@/api/discovery";
import { useDiscovery } from "@/hooks/useDiscovery";
import { useKnowledgeRun } from "@/hooks/useKnowledgeRun";
const tabs = [
  ["all", "All", Layers],
  ["product", "Products", Box],
  ["data", "Data", Database],
  ["document", "Documents", FileText],
] as const;
function SearchResults() {
  const params = useSearchParams(),
    router = useRouter();
  const { persona, token } = useSession();
  const query = (params.get("q") || "").trim(),
    domainId = params.get("domain_id");
  const type = ["all", "product", "data", "document"].includes(
    params.get("type") || "",
  )
    ? params.get("type")!
    : "all";
  const sort = params.get("sort") === "name" ? "name" : "relevance",
    page = Math.max(1, Number(params.get("page") || 1) || 1);
  const selected = params.get("selected"),
    selectedKind =
      params.get("detail_kind") === "product" ? "product" : "asset";
  const [evidence, setEvidence] = useState("");
  const [citedQuote, setCitedQuote] = useState<string | undefined>();
  const results = useDiscovery({ query, domainId, type, sort, page }, token),
    answer = useKnowledgeRun({ query, domainId, persona }, token);
  function update(change: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(change)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    window.history.pushState(null, "", "/search?" + next);
  }
  const closeDetail = useCallback(() => {
    const next = new URLSearchParams(window.location.search);
    next.delete("selected");
    next.delete("detail_kind");
    next.delete("selected_locator");
    next.delete("selected_version");
    next.delete("selected_source");
    window.history.replaceState(null, "", "/search?" + next);
  }, []);
  const closeEvidence = useCallback(() => setEvidence(""), []);
  function select(item: DiscoveryItem) {
    update({
      selected: item.id,
      detail_kind: item.kind === "product" ? "product" : "asset",
      selected_locator: item.content_handle?.locator || null,
      selected_version: item.content_handle?.version || null,
      selected_source:
        item.kind === "product" ? item.source_ref?.asset_id || null : null,
    });
  }
  if (query.length < 3)
    return (
      <div className="search-entry">
        <h1>What would you like to know?</h1>
        <p>Find products, data, and documents. Get an answer with evidence.</p>
        <SearchBox
          onSubmit={(value) => router.push(prepareSearch(value, persona))}
        />
        <Link href="/catalog">
          Or browse the catalog <ArrowRight size={15} />
        </Link>
      </div>
    );
  return (
    <div className="discovery-results-page">
      <SearchHeader query={query} domainId={domainId} />
      <div className="discovery-tabs" aria-label="Result type">
        {tabs.map(([value, label, Icon]) => (
          <button
            key={value}
            aria-pressed={type === value}
            className={type === value ? "selected" : ""}
            onClick={() =>
              update({
                type: value === "all" ? null : value,
                page: null,
                selected: null,
                detail_kind: null,
              })
            }
          >
            {type === value && (
              <motion.span
                layoutId="result-tab-indicator"
                className="result-tab-indicator"
                aria-hidden="true"
              />
            )}
            <Icon size={17} />
            {label}
          </button>
        ))}
        <select
          aria-label="Sort results"
          value={sort}
          onChange={(e) =>
            update({
              sort: e.target.value === "relevance" ? null : e.target.value,
              page: null,
            })
          }
        >
          <option value="relevance">Relevance</option>
          <option value="name">Name A–Z</option>
        </select>
      </div>
      <div className="discovery-results-layout">
        <div className="discovery-results-primary">
          <AnswerPanel
            run={answer.run}
            busy={answer.busy}
            error={answer.error}
            domainId={domainId}
            onGenerate={answer.submit}
            onCancel={answer.cancel}
            onReconnect={answer.reconnect}
            onEvidence={(id, quote) => {
              setEvidence(id);
              setCitedQuote(quote);
            }}
          />
          <div className="results-heading">
            <h2>Top matches</h2>
            <span>
              {results.data?.returned_count ?? "…"} shown
              {domainId && (
                <>
                  {" "}
                  · <DomainName id={domainId} />
                </>
              )}
            </span>
          </div>
          {results.error ? (
            <div className="results-error" role="alert">
              <strong>Search results unavailable</strong>
              <p>{results.error}</p>
              <button onClick={results.retry}>Try search again</button>
            </div>
          ) : results.loading ? (
            <Loading />
          ) : results.data?.items.length ? (
            <>
              <ResultList items={results.data.items} onSelect={select} />
              <div className="results-pagination">
                <button
                  disabled={page === 1}
                  onClick={() =>
                    update({ page: page > 2 ? String(page - 1) : null })
                  }
                  aria-label="Previous results"
                >
                  Previous
                </button>
                <span>Page {page}</span>
                <button
                  disabled={!results.data.has_more}
                  onClick={() => update({ page: String(page + 1) })}
                  aria-label="Next results"
                >
                  Next <ArrowRight size={13} />
                </button>
              </div>
            </>
          ) : (
            <Loading loading={false} />
          )}
        </div>
        <aside className="discovery-results-aside">
          <div className="search-context">
            <ShieldCheck size={21} />
            <h3>Connected. Governed. Cited.</h3>
            <p>
              Your search follows relationships across the knowledge you can
              access.
            </p>
            <span className="context-scope">
              {domainId ? (
                <DomainName id={domainId} />
              ) : (
                "All authorized domains"
              )}
            </span>
            <Link
              href={
                "/catalog" +
                (domainId ? "?domain_id=" + encodeURIComponent(domainId) : "")
              }
            >
              Browse this catalog <ArrowRight size={14} />
            </Link>
          </div>
          {results.data?.items.some((item) => item.kind === "product") && (
            <div className="related-products">
              <h3>Related products</h3>
              {results.data.items
                .filter((item) => item.kind === "product")
                .slice(0, 3)
                .map((item) => (
                  <Link
                    key={item.id}
                    href={"/catalog?selected=" + encodeURIComponent(item.id)}
                  >
                    <Box size={17} />
                    <span>{item.title}</span>
                    <ArrowRight size={13} />
                  </Link>
                ))}
            </div>
          )}
          {answer.run?.graph.edges.length ? (
            <details className="search-ontology">
              <summary>
                Ontology context <ChevronDown size={14} />
              </summary>
              {answer.run.graph.edges.slice(0, 6).map((edge, i) => (
                <p key={i}>
                  {answer.run?.graph.nodes.find((n) => n.id === edge.source)
                    ?.name || edge.source}{" "}
                  <span>{edge.label}</span>{" "}
                  {answer.run?.graph.nodes.find((n) => n.id === edge.target)
                    ?.name || edge.target}
                </p>
              ))}
              <Link href="/ontology">
                Explore relationships <ArrowRight size={13} />
              </Link>
            </details>
          ) : null}
        </aside>
      </div>
      {selected && (
        <DiscoveryDetail
          key={
            selected +
            selectedKind +
            token +
            params.get("selected_locator") +
            params.get("selected_version") +
            params.get("selected_source")
          }
          id={selected}
          kind={selectedKind}
          locator={params.get("selected_locator") || undefined}
          version={params.get("selected_version") || undefined}
          preferredAsset={params.get("selected_source") || undefined}
          onClose={closeDetail}
        />
      )}
      {evidence &&
        answer.run?.evidence.some((item) => item.id === evidence) && (
          <EvidenceDetail
            key={evidence + token}
            id={evidence}
            runId={answer.run?.run_id}
            quote={citedQuote}
            onClose={closeEvidence}
          />
        )}
    </div>
  );
}
export default function Search() {
  return (
    <Suspense fallback={<Loading />}>
      <SearchResults />
    </Suspense>
  );
}
