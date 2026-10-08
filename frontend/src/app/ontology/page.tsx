"use client";
import { useEffect, useState } from "react";
import type { components } from "@/api/generated";
import { useData } from "@/api/client";
import { useSession } from "@/components/Shell";
import { PageHeading, Loading, Badge, Modal } from "@/components/Common";
import OntologyGraph from "@/components/discovery/OntologyGraph";
import ContentViewer from "@/components/discovery/ContentViewer";

export default function Ontology() {
  const { token } = useSession();
  const [concept, setConcept] = useState("Counterparty");
  const [selected, setSelected] = useState("");
  const [depth, setDepth] = useState("2");
  const [handle, setHandle] = useState<
    components["schemas"]["ContentHandle"] | null
  >(null);
  const [rdf, setRdf] = useState(false);
  const [validate, setValidate] = useState(false);
  useEffect(() => {
    const requested = new URLSearchParams(location.search).get("concept");
    if (requested) setConcept(requested);
  }, []);
  const concepts = useData<{ id: string; name: string; iri: string }[]>(
    "/ontology/concepts",
    token,
  );
  const graph = useData<components["schemas"]["GraphPage"]>(
    "/ontology/neighborhood?concept_id=" +
      encodeURIComponent(concept) +
      "&depth=" +
      depth +
      "&limit=50",
    token,
  );
  const turtle = useData<{ turtle: string }>(
    rdf ? "/ontology/rdf" : null,
    token,
  );
  const findings = useData<{ asset_id: string; message: string }[]>(
    validate ? "/ontology/findings" : null,
    token,
  );
  const node =
    graph.data?.nodes.find((node) => node.id === selected) ||
    graph.data?.nodes.find((node) => node.id === graph.data?.root) ||
    graph.data?.nodes[0];
  function change(id: string) {
    setConcept(id);
    setSelected("");
    history.replaceState(
      null,
      "",
      "/ontology?concept=" + encodeURIComponent(id),
    );
  }
  return (
    <>
      <PageHeading
        title="Ontology explorer"
        description="Follow governing relationships from business concepts to the actual source content."
        action={
          <button className="btn btn-secondary" onClick={() => setRdf(true)}>
            Inspect RDF
          </button>
        }
      />
      <div className="ontology-context-tools">
        <label>
          Starting concept{" "}
          <select
            aria-label="Starting ontology concept"
            value={concept}
            onChange={(event) => change(event.target.value)}
          >
            {!concepts.data?.some((item) => item.id === concept) && (
              <option value={concept}>{concept}</option>
            )}
            {concepts.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Explore{" "}
          <select
            aria-label="Graph depth"
            value={depth}
            onChange={(event) => setDepth(event.target.value)}
          >
            <option value="1">One relationship away</option>
            <option value="2">Two relationships away</option>
            <option value="3">Three relationships away</option>
          </select>
        </label>
      </div>
      {graph.loading || graph.error ? (
        <Loading error={graph.error} />
      ) : (
        graph.data && (
          <div className="ontology-workspace">
            <OntologyGraph
              graph={graph.data}
              selected={node?.id || ""}
              onSelect={setSelected}
            />
            <aside className="ontology-inspector">
              <span className="eyebrow">SELECTED NODE</span>
              {node && (
                <>
                  <h2>{node.name}</h2>
                  <Badge tone="neutral">{node.kind}</Badge>
                  {node.status && <p>{node.status}</p>}
                  <p className="source-location">{node.iri}</p>
                  <button
                    className="btn btn-primary"
                    onClick={() => setHandle(node.content_handle)}
                  >
                    Open source content
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => change(node.id)}
                  >
                    Expand neighborhood
                  </button>
                  <h3>Connected relationships</h3>
                  {graph.data.edges
                    .filter(
                      (edge) =>
                        edge.source === node.id || edge.target === node.id,
                    )
                    .map((edge, index) => (
                      <div className="ontology-edge-detail" key={index}>
                        <strong>{edge.label}</strong>
                        <p>
                          {
                            graph.data!.nodes.find(
                              (item) => item.id === edge.source,
                            )?.name
                          }{" "}
                          →{" "}
                          {
                            graph.data!.nodes.find(
                              (item) => item.id === edge.target,
                            )?.name
                          }
                        </p>
                        {edge.source_ref && (
                          <button
                            onClick={() =>
                              setHandle({
                                kind: "asset",
                                id: edge.source_ref!.asset_id,
                                locator: edge.source_ref!.locator,
                                version: edge.source_ref!.version,
                              })
                            }
                          >
                            View supporting passage
                          </button>
                        )}
                      </div>
                    ))}
                </>
              )}
            </aside>
          </div>
        )
      )}
      <details
        className="ontology-validation"
        onToggle={(event) => setValidate(event.currentTarget.open)}
      >
        <summary>Governance validation</summary>
        {findings.loading || findings.error ? (
          <Loading error={findings.error} />
        ) : findings.data?.length ? (
          findings.data.map((finding, index) => (
            <p key={index}>
              {finding.message}{" "}
              <button
                onClick={() =>
                  setHandle({ kind: "asset", id: finding.asset_id })
                }
              >
                Open source
              </button>
            </p>
          ))
        ) : (
          <p>No SHACL findings within your access scope.</p>
        )}
      </details>
      {rdf && (
        <Modal
          title="RDF vocabulary and instances"
          onClose={() => setRdf(false)}
        >
          <div className="modal-body">
            {turtle.loading || turtle.error ? (
              <Loading error={turtle.error} />
            ) : (
              <pre className="source-code">{turtle.data?.turtle}</pre>
            )}
          </div>
        </Modal>
      )}
      {handle && (
        <ContentViewer
          key={JSON.stringify(handle) + token}
          handle={handle}
          onClose={() => setHandle(null)}
        />
      )}
    </>
  );
}
