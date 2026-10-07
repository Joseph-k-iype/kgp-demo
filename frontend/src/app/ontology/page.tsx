"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Network,
  Code,
  List,
  Share2,
  ChevronRight,
  ArrowUpRight,
  ShieldCheck,
  Search,
} from "lucide-react";
import { useData, GraphData } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  PageHeading,
  Loading,
  Badge,
  PanelHeading,
  Modal,
} from "@/components/Common";
import Graph from "@/components/Graph";
import AssetDetail from "@/components/AssetDetail";
export default function Ontology() {
  const { token } = useSession();
  const [concept, setConcept] = useState("Counterparty"),
    [view, setView] = useState("graph"),
    [selected, setSelected] = useState("Counterparty"),
    [rdf, setRdf] = useState(false),
    [asset, setAsset] = useState(""),
    [filter, setFilter] = useState("");
  useEffect(() => {
    const c = new URLSearchParams(location.search).get("concept");
    if (c) {
      setConcept(c);
      setSelected(c);
    }
  }, []);
  const concepts = useData<{ id: string; name: string; iri: string }[]>(
      "/ontology/concepts",
      token,
    ),
    graph = useData<GraphData>(
      "/ontology/neighborhood?concept_id=" +
        encodeURIComponent(concept) +
        "&depth=1&limit=13",
      token,
    ),
    findings = useData<{ asset_id: string; message: string }[]>(
      "/ontology/findings",
      token,
    ),
    turtle = useData<{ turtle: string }>(rdf ? "/ontology/rdf" : null, token);
  const node =
    graph.data?.nodes.find((n) => n.id === selected) || graph.data?.nodes[0];
  function change(c: string) {
    setConcept(c);
    setSelected(c);
    history.replaceState(
      null,
      "",
      "/ontology?concept=" + encodeURIComponent(c),
    );
  }
  return (
    <>
      <PageHeading
        title="Ontology explorer"
        description="Explore the meaning and relationships that govern your underlying knowledge assets."
        action={
          <button className="btn btn-secondary" onClick={() => setRdf(true)}>
            <Code size={14} /> Inspect RDF
          </button>
        }
      />
      <div
        className="notice"
        style={{
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          gap: 9,
        }}
      >
        <ShieldCheck size={16} /> RDF / RDFS vocabulary · Asserted relationships
        · Scope-aware SPARQL · SHACL constraints
      </div>
      <div className="graph-layout">
        <aside className="panel">
          <PanelHeading title="Concepts" />
          <div className="panel-body" style={{ padding: 10 }}>
            <div className="search-input">
              <Search size={12} />
              <input
                aria-label="Find ontology concept"
                placeholder="Find concept…"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </div>
          </div>
          <div className="concept-list">
            {concepts.data
              ?.filter((c) =>
                c.name.toLowerCase().includes(filter.toLowerCase()),
              )
              .map((c) => (
                <button
                  key={c.id}
                  className={concept === c.id ? "active" : ""}
                  onClick={() => change(c.id)}
                >
                  <Network size={14} />
                  {c.name}
                </button>
              ))}
          </div>
        </aside>
        <section className="panel">
          <div className="graph-toolbar">
            <span>
              {graph.data?.nodes.length || "—"} nodes ·{" "}
              {graph.data?.edges.length || "—"} relationships
            </span>
            <div className="segmented">
              <button
                aria-label="Graph view"
                className={view === "graph" ? "active" : ""}
                onClick={() => setView("graph")}
              >
                <Share2 size={13} /> Graph
              </button>
              <button
                aria-label="List view"
                className={view === "list" ? "active" : ""}
                onClick={() => setView("list")}
              >
                <List size={13} /> List
              </button>
            </div>
          </div>
          {graph.loading || graph.error ? (
            <Loading error={graph.error} />
          ) : graph.data && view === "graph" ? (
            <Graph
              data={graph.data}
              selected={selected}
              onSelect={setSelected}
            />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>NODE</th>
                    <th>TYPE</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {graph.data?.nodes.map((n) => (
                    <tr
                      key={n.id}
                      className="clickable"
                      onClick={() => setSelected(n.id)}
                    >
                      <td>
                        <button onClick={() => setSelected(n.id)}>
                          {n.name}
                        </button>
                      </td>
                      <td>
                        <Badge tone={n.kind === "Concept" ? "teal" : "neutral"}>
                          {n.kind}
                        </Badge>
                      </td>
                      <td>
                        <ChevronRight size={12} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="panel-body">
            <p className="metric-note">
              {graph.data?.truncated
                ? "Neighborhood is bounded to 13 nodes. Expand a selected node to explore further."
                : "Select a node to inspect its definition, provenance, and relationships."}
            </p>
          </div>
        </section>
        <aside className="panel detail-panel">
          <PanelHeading title="Node details" />
          {node ? (
            <>
              <div className="panel-body">
                <span className="asset-icon teal">
                  <Network size={20} />
                </span>
                <h2 style={{ margin: "15px 0 10px" }}>{node.name}</h2>
                <Badge tone="teal">{node.kind}</Badge>
                <p className="source-location" style={{ marginTop: 16 }}>
                  {node.iri}
                </p>
                <p style={{ fontSize: 11, marginTop: 14, lineHeight: 1.8 }}>
                  {node.kind === "Concept"
                    ? "A shared business concept connecting structured records, documents, and governed products."
                    : "An asserted catalog entity linked to its source, business domain and governing ontology."}
                </p>
                <button
                  className="btn btn-secondary"
                  style={{ width: "100%", marginTop: 20 }}
                  onClick={() => change(node.id)}
                >
                  Expand neighborhood <ArrowUpRight size={13} />
                </button>
                {node.id.includes("-asset-") && (
                  <button
                    className="btn btn-primary"
                    style={{ width: "100%", marginTop: 9 }}
                    onClick={() => setAsset(node.id)}
                  >
                    Inspect source asset <ArrowUpRight size={13} />
                  </button>
                )}
              </div>
              <div className="detail-section">
                <h3>Asserted relationships</h3>
                {graph.data?.edges
                  .filter((e) => e.source === node.id || e.target === node.id)
                  .map((e, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "7px 0",
                        fontSize: 10,
                        borderBottom: "1px solid #edf1f6",
                      }}
                    >
                      <span style={{ color: "#0876f9" }}>{e.label}</span>
                      <p
                        style={{
                          fontSize: 9,
                          marginTop: 3,
                          wordBreak: "break-word",
                        }}
                      >
                        {e.source} → {e.target}
                      </p>
                    </div>
                  ))}
              </div>
            </>
          ) : (
            <Loading />
          )}
        </aside>
      </div>
      <section className="panel section-space">
        <PanelHeading
          title="Ontology governance findings"
          action={
            <Badge tone={findings.data?.length ? "amber" : "teal"}>
              {findings.data?.length || 0} findings
            </Badge>
          }
        />
        <div className="panel-body">
          {findings.data?.length ? (
            findings.data.map((f) => (
              <div className="notice amber" key={f.asset_id}>
                <div className="spaced">
                  <div>
                    <strong>Missing asserted stewardship</strong>
                    <p style={{ fontSize: 11, marginTop: 4 }}>{f.message}</p>
                    <p className="metric-note">
                      Deliberately seeded RDF issue · {f.asset_id}
                    </p>
                  </div>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setAsset(f.asset_id)}
                  >
                    Inspect asset
                  </button>
                </div>
              </div>
            ))
          ) : (
            <p className="small-text">No SHACL findings within your scope.</p>
          )}
        </div>
      </section>
      {rdf && (
        <Modal title="RDF vocabulary & instances" onClose={() => setRdf(false)}>
          <div className="modal-body">
            <p style={{ marginBottom: 15 }}>
              Read-only Turtle representation from Fuseki, filtered to your
              access scope.
            </p>
            {turtle.loading || turtle.error ? (
              <Loading error={turtle.error} />
            ) : (
              <pre className="source-code">{turtle.data?.turtle}</pre>
            )}
          </div>
        </Modal>
      )}
      {asset && <AssetDetail id={asset} onClose={() => setAsset("")} />}
    </>
  );
}
