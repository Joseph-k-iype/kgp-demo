"use client";
import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  Search,
  ArrowRight,
  Check,
  Network,
  Database,
  FileText,
  ExternalLink,
  Square,
  Code,
  ShieldCheck,
} from "lucide-react";
import { api, useData, Run, Evidence, streamRun } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  PageHeading,
  Badge,
  Modal,
  Loading,
  PanelHeading,
  DomainName,
} from "@/components/Common";
export default function AgentSearch() {
  const { token, persona } = useSession();
  const [query, setQuery] = useState(""),
    [mode, setMode] = useState("llm"),
    [run, setRun] = useState<Run | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [evidenceId, setEvidenceId] = useState("");
  const controller = useRef<AbortController | null>(null);
  const health = useData<{ llm: { configured: boolean; model: string } }>(
    "/health",
    token,
  );
  const evidence = useData<Evidence>(
    evidenceId ? "/evidence/" + encodeURIComponent(evidenceId) : null,
    token,
  );
  async function follow(id: string) {
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    try {
      await streamRun(
        id,
        token,
        (event) =>
          setRun((r) =>
            r
              ? {
                  ...r,
                  events: [
                    ...r.events.filter((e) => e.sequence !== event.sequence),
                    event,
                  ].sort((a, b) => a.sequence - b.sequence),
                }
              : r,
          ),
        (result) => {
          setRun(result);
          setBusy(false);
        },
        c.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        const result = await api<Run>("/search/runs/" + id, token);
        setRun(result);
        setBusy(result.status === "pending" || result.status === "running");
        setError(
          "Progress connection interrupted. Reload to reconnect to the same search.",
        );
      }
    }
  }
  useEffect(() => {
    const id = sessionStorage.getItem("atlas-search-" + persona);
    if (id)
      api<Run>("/search/runs/" + id, token)
        .then((r) => {
          setRun(r);
          setQuery(r.query);
          setMode(r.mode);
          if (["pending", "running"].includes(r.status)) follow(id);
        })
        .catch(() => sessionStorage.removeItem("atlas-search-" + persona));
    return () => controller.current?.abort();
  }, [token, persona]);
  async function search() {
    if (query.trim().length < 3) return;
    setError("");
    setBusy(true);
    try {
      const r = await api<Run>("/search/runs", token, {
        method: "POST",
        body: JSON.stringify({ query, mode }),
      });
      setRun(r);
      sessionStorage.setItem("atlas-search-" + persona, r.run_id);
      await follow(r.run_id);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  async function cancel() {
    if (!run) return;
    const r = await api<Run>("/search/runs/" + run.run_id + "/cancel", token, {
      method: "POST",
    });
    controller.current?.abort();
    setRun(r);
    setBusy(false);
  }
  const completed = run?.status === "completed";
  const suggestions = [
    "Find counterparty exposure and due diligence evidence",
    "Which policies govern treasury liquidity?",
    "Show technology service health sources",
  ];
  return (
    <>
      <PageHeading
        title="Ask your knowledge estate"
        description="Agentic search that follows meaning, finds evidence, and shows you where every answer comes from."
        action={
          <Badge tone="violet">
            <Sparkles size={12} /> LangGraph + DeepSeek
          </Badge>
        }
      />
      <div className="search-layout">
        <div>
          <section className="panel search-box">
            <div className="spaced" style={{ marginBottom: 15 }}>
              <h2>
                <Sparkles size={17} color="#0876f9" /> Agentic knowledge search
              </h2>
              <Badge tone="teal">
                <ShieldCheck size={11} /> Scoped to your access
              </Badge>
            </div>
            <textarea
              aria-label="Ask a knowledge question"
              placeholder="Ask a question across products, structured data, and documents…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  search();
                }
              }}
            />
            <div className="search-controls">
              <div className="actions-row">
                <select
                  aria-label="Search mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  disabled={busy}
                >
                  <option value="llm">DeepSeek · OpenRouter</option>
                  <option value="extractive">
                    Extractive demo · Source excerpts
                  </option>
                </select>
                <span className="metric-note">⌘ ↵ to search</span>
              </div>
              {busy ? (
                <button className="btn btn-secondary" onClick={cancel}>
                  <Square size={12} /> Cancel search
                </button>
              ) : (
                <button
                  className="btn btn-primary"
                  onClick={search}
                  disabled={query.trim().length < 3}
                >
                  <Search size={14} /> Search knowledge <ArrowRight size={13} />
                </button>
              )}
            </div>
            <div className="suggestions">
              {suggestions.map((q) => (
                <button key={q} onClick={() => setQuery(q)}>
                  {q}
                </button>
              ))}
            </div>
            {!health.data?.llm.configured && mode !== "extractive" && (
              <div className="notice amber" style={{ marginTop: 17 }}>
                OpenRouter is not configured yet. Set the server OpenRouter API
                key to enable LLM synthesis, or choose Extractive demo to
                explore real retrieval with source excerpts.
              </div>
            )}
            {error && (
              <div className="inline-error" style={{ marginTop: 15 }}>
                {error}
              </div>
            )}
          </section>
          {!run ? (
            <section className="panel search-intro section-space">
              <span className="asset-icon">
                <Network size={25} />
              </span>
              <h2>One question. Connected knowledge.</h2>
              <p>
                Knowledge Product Manager resolves ontology concepts, searches
                keyword and vector indexes, and connects structured records with
                document evidence. Every result keeps its provenance.
              </p>
              <div
                className="formats"
                style={{ justifyContent: "center", marginTop: 22 }}
              >
                <Badge>PostgreSQL</Badge>
                <Badge tone="neutral">MinIO documents</Badge>
                <Badge tone="teal">RDF context</Badge>
                <Badge tone="violet">OpenSearch vectors</Badge>
              </div>
            </section>
          ) : (
            <>
              <section className="panel section-space">
                <PanelHeading
                  title={
                    completed
                      ? "Search completed"
                      : busy
                        ? "Searching your knowledge estate…"
                        : run.status === "configuration_required"
                          ? "OpenRouter configuration required"
                          : run.status === "cancelled"
                            ? "Search cancelled"
                            : "Search could not complete"
                  }
                  action={
                    <Badge tone={completed ? "teal" : busy ? "blue" : "amber"}>
                      {run.mode === "extractive"
                        ? "Extractive demo"
                        : "DeepSeek synthesis"}
                    </Badge>
                  }
                />
                <div className="answer-body">
                  {run.error ? (
                    <div className="notice amber">{run.error}</div>
                  ) : busy ? (
                    <Loading />
                  ) : run.statements.length ? (
                    run.statements.map((s, i) => (
                      <div className="answer-statement" key={i}>
                        {s.text}
                        <div style={{ marginTop: 6 }}>
                          {s.evidence_ids.map((id) => {
                            const number =
                              run.evidence.findIndex((e) => e.id === id) + 1;
                            return (
                              <button
                                key={id}
                                className="citation"
                                aria-label={"Open evidence " + number}
                                onClick={() => setEvidenceId(id)}
                              >
                                <ExternalLink size={10} /> Source {number}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="small-text">
                      {run.gaps[0] || "No answer has been generated."}
                    </p>
                  )}
                  {run.uncertainty && (
                    <div className="notice" style={{ marginTop: 16 }}>
                      {run.uncertainty}
                    </div>
                  )}
                  {run.gaps.length > 0 && (
                    <div className="notice amber" style={{ marginTop: 12 }}>
                      <strong>Coverage gaps</strong>
                      {run.gaps.map((g, i) => (
                        <p
                          key={i}
                          className="small-text"
                          style={{ marginTop: 5 }}
                        >
                          {g}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </section>
              {completed && run.evidence.length > 0 && (
                <section className="panel section-space">
                  <PanelHeading
                    title="Retrieved evidence"
                    action={
                      <Badge tone="neutral">
                        {run.evidence.length} source excerpts
                      </Badge>
                    }
                  />
                  <div className="panel-body">
                    {run.evidence.map((e, i) => (
                      <button
                        key={e.id}
                        className="evidence-card"
                        style={{ width: "100%", textAlign: "left" }}
                        onClick={() => setEvidenceId(e.id)}
                      >
                        <div className="spaced">
                          <Badge
                            tone={
                              e.provenance.type === "document"
                                ? "violet"
                                : e.provenance.type === "structured"
                                  ? "blue"
                                  : "teal"
                            }
                          >
                            {e.provenance.type === "document" ? (
                              <FileText size={11} />
                            ) : (
                              <Database size={11} />
                            )}{" "}
                            {e.provenance.type}
                          </Badge>
                          <span className="muted" style={{ fontSize: 9 }}>
                            Source {i + 1} · <DomainName id={e.domain_id} />
                          </span>
                        </div>
                        <h3>{e.name}</h3>
                        <p>{e.text}</p>
                      </button>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
        <aside>
          <section className="panel">
            <PanelHeading
              title="Search workflow"
              action={<Badge tone="neutral">LangGraph</Badge>}
            />
            {run?.events.length
              ? run.events.map((e, i) => (
                  <div className="trace-step" key={e.sequence}>
                    <span className="trace-marker">
                      {i < run.events.length - 1 || completed ? (
                        <Check size={12} />
                      ) : busy ? (
                        <span
                          className="dot"
                          style={{ background: "#0876f9" }}
                        />
                      ) : (
                        i + 1
                      )}
                    </span>
                    <div>
                      <h3>
                        {e.stage === "resolve"
                          ? "Ontology resolution"
                          : e.stage === "expand"
                            ? "Evidence provenance"
                            : e.stage === "validate"
                              ? "Citation validation"
                              : e.stage}
                      </h3>
                      <p>{e.summary}</p>
                    </div>
                  </div>
                ))
              : [
                  "Resolve business meaning",
                  "Retrieve keywords & vectors",
                  "Follow RDF relationships",
                  "Check evidence coverage",
                  "Compose a cited answer",
                ].map((s, i) => (
                  <div className="trace-step" key={s}>
                    <span className="trace-marker">{i + 1}</span>
                    <div>
                      <h3>{s}</h3>
                      <p>Runs after you submit a question</p>
                    </div>
                  </div>
                ))}
            <div className="panel-body">
              <p className="metric-note">
                Two retrieval passes · 12 tool calls · 90 second deadline
              </p>
            </div>
          </section>
          {run && run.graph?.edges?.length > 0 && (
            <section className="panel mcp-box">
              <h2>Graph context</h2>
              {run.graph.edges.slice(0, 5).map((e, i) => (
                <div key={i} style={{ marginTop: 12, fontSize: 10 }}>
                  <span className="text-link">{e.label}</span>
                  <p style={{ fontSize: 9, wordBreak: "break-word" }}>
                    {e.source} → {e.target}
                  </p>
                </div>
              ))}
            </section>
          )}
          <section className="panel mcp-box">
            <div className="spaced">
              <h2>Available through MCP</h2>
              <Code size={17} />
            </div>
            <p>
              Use the same governed catalog, ontology and search tools from an
              MCP client.
            </p>
            <code>http://127.0.0.1:58123/mcp</code>
            <p>
              Tools: search_catalog, explore_ontology, get_evidence,
              agentic_search, and more.
            </p>
            <a
              className="text-link"
              href="http://127.0.0.1:58123/docs"
              target="_blank"
              rel="noreferrer"
            >
              Inspect API contracts <ExternalLink size={11} />
            </a>
          </section>
        </aside>
      </div>
      {evidenceId && (
        <Modal title="Source evidence" onClose={() => setEvidenceId("")}>
          <div className="modal-body">
            {evidence.loading || evidence.error ? (
              <Loading error={evidence.error} />
            ) : (
              evidence.data && (
                <>
                  <div className="spaced">
                    <h3>{evidence.data.name}</h3>
                    <Badge>{evidence.data.provenance.type}</Badge>
                  </div>
                  <p className="source-location" style={{ margin: "12px 0" }}>
                    {evidence.data.provenance.location}
                  </p>
                  <pre className="source-code">{evidence.data.text}</pre>
                  <div className="notice" style={{ marginTop: 16 }}>
                    Stable evidence ID: {evidence.data.id}
                    <br />
                    {evidence.data.provenance.row_id
                      ? "PostgreSQL row: " + evidence.data.provenance.row_id
                      : evidence.data.provenance.object_key
                        ? "MinIO object: " +
                          evidence.data.provenance.object_key +
                          " · offsets " +
                          evidence.data.provenance.start +
                          "–" +
                          evidence.data.provenance.end
                        : "Catalog metadata evidence"}
                    <br />
                    Synthetic information · Access checked on read
                  </div>
                </>
              )
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
