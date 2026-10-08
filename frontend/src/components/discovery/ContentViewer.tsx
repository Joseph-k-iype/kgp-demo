"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import type { components } from "@/api/generated";
import { useData } from "@/api/client";
import { useSession } from "@/components/Shell";
import { Loading, Modal } from "@/components/Common";
import SourceMarkdown from "./SourceMarkdown";

type Handle = components["schemas"]["ContentHandle"];
type Content = components["schemas"]["ContentPage"];
function object(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
function text(value: unknown): string {
  if (value == null) return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
function Context({ value }: { value: Record<string, unknown> }) {
  return (
    <div className="reader-context">
      {Object.entries(value).map(([section, data]) => (
        <section key={section}>
          <h3>{section.replaceAll("_", " ")}</h3>
          <dl>
            {Object.entries(object(data))
              .filter(
                ([key]) =>
                  !["payload", "assets", "product_ids", "concepts"].includes(
                    key,
                  ),
              )
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{text(value)}</dd>
                </div>
              ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
export default function ContentViewer({
  handle,
  onClose,
  quote,
  preferredAsset,
}: {
  handle: Handle;
  onClose: () => void;
  quote?: string;
  preferredAsset?: string;
}) {
  const { token } = useSession();
  const [tab, setTab] = useState("Content");
  const [related, setRelated] = useState<Handle | null>(null);
  const activeHandle = related || handle;
  const [preferred, setPreferred] = useState(preferredAsset || "");
  const [cursor, setCursor] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const query = new URLSearchParams();
  if (cursor) query.set("cursor", cursor);
  const sameSource =
    activeHandle.kind !== "product" ||
    !preferred ||
    preferred === preferredAsset;
  for (const key of ["locator", "version", "run_id", "evidence_id"] as const)
    if (
      !related &&
      handle[key] &&
      (sameSource || !["locator", "version"].includes(key))
    )
      query.set(key, handle[key]!);
  if (preferred && !related) query.set("preferred_asset_id", preferred);
  const path =
    activeHandle.kind === "product"
      ? "/products/" + encodeURIComponent(activeHandle.id) + "/content"
      : "/content/" +
        activeHandle.kind +
        "/" +
        encodeURIComponent(activeHandle.id);
  const content = useData<Content>(path + "?" + query, token);
  const productDetail = useData<Record<string, unknown>>(
    !related && handle.kind === "product" && tab === "Context"
      ? "/products/" + encodeURIComponent(handle.id)
      : null,
    token,
  );
  const data = content.data;
  const [manifestCache, setManifestCache] = useState<{
    token: string;
    id: string;
    manifest: NonNullable<Content["manifest"]>;
  } | null>(null);
  useEffect(() => {
    if (data?.manifest)
      setManifestCache({ token, id: handle.id, manifest: data.manifest });
  }, [data, token, handle.id]);
  const manifest = related
    ? null
    : data?.manifest ||
      (manifestCache?.token === token && manifestCache.id === handle.id
        ? manifestCache.manifest
        : null);

  const columns = (data?.columns || []).map((column) => ({
    name: text(column.name),
    unit: column.unit ? text(column.unit) : "",
  }));
  const record = object(data?.context?.record);
  const concepts = Array.isArray(record.concepts) ? record.concepts : [];
  return (
    <Modal
      className="content-reader"
      title={manifest?.title || data?.title || "Opening source content…"}
      onClose={onClose}
    >
      <div className="reader-tabs" role="tablist" aria-label="Source view">
        {["Content", "Context", "Relationships"].map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={tab === name}
            aria-controls="reader-panel"
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <div
        className="reader-body"
        id="reader-panel"
        role="tabpanel"
        aria-label={tab}
      >
        {manifest && (
          <label className="reader-source-picker">
            Source{" "}
            <select
              aria-label="Product source"
              value={preferred || manifest.primary?.id || ""}
              onChange={(event) => {
                setPreferred(event.target.value);
                setCursor("");
                setHistory([]);
                setTab("Content");
              }}
            >
              {manifest.sources?.map((source) => (
                <option key={source.handle.id} value={source.handle.id}>
                  {source.title} · {source.source_type}
                </option>
              ))}
            </select>
          </label>
        )}
        {content.loading || content.error ? (
          <Loading error={content.error} />
        ) : (
          data && (
            <>
              {data.freshness === "changed" && (
                <div className="notice" role="status">
                  This source changed since the answer was produced. The content
                  below is current.{" "}
                  {data.cited_snapshot
                    ? "The cited snapshot is shown separately."
                    : "The earlier version is not available in this view."}
                </div>
              )}
              {tab === "Content" && (
                <>
                  <div className="reader-title">
                    <span>
                      {data.content_type === "dataset"
                        ? "DATASET"
                        : data.content_type === "definition"
                          ? "ONTOLOGY DEFINITION"
                          : "SOURCE DOCUMENT"}
                    </span>
                    <h1>{data.title}</h1>
                  </div>
                  {related && (
                    <button
                      className="btn btn-secondary"
                      onClick={() => {
                        setRelated(null);
                        setCursor("");
                        setHistory([]);
                      }}
                    >
                      Back to original source
                    </button>
                  )}
                  {data.aggregate && (
                    <section className="reader-aggregate">
                      <h3>Calculated result</h3>
                      <p>
                        {text(data.aggregate.operation)} of{" "}
                        {text(data.aggregate.field || "selected records")}
                      </p>
                      <dl>
                        {Object.entries(object(data.aggregate.values)).map(
                          ([key, value]) => (
                            <div key={key}>
                              <dt>{key.replaceAll("_", " ")}</dt>
                              <dd>{text(value)}</dd>
                            </div>
                          ),
                        )}
                      </dl>
                      <p>
                        Included:{" "}
                        {Array.isArray(data.aggregate.filters) &&
                        data.aggregate.filters.length
                          ? data.aggregate.filters
                              .map((filter) => {
                                const f = object(filter);
                                const operators: Record<string, string> = {
                                  eq: "is",
                                  gt: "is greater than",
                                  gte: "is at least",
                                  lt: "is less than",
                                  lte: "is at most",
                                  in: "is one of",
                                };
                                return (
                                  text(f.field).replaceAll("_", " ") +
                                  " " +
                                  (operators[text(f.op)] || text(f.op)) +
                                  " " +
                                  (Array.isArray(f.value)
                                    ? f.value.join(", ")
                                    : text(f.value))
                                );
                              })
                              .join("; ")
                          : "all source records"}
                      </p>
                      <h3>Underlying selection</h3>
                    </section>
                  )}
                  {!related && sameSource && quote && (
                    <blockquote className="reader-cited-passage">
                      <strong>Cited passage</strong>
                      <p>{quote}</p>
                    </blockquote>
                  )}
                  {data.cited_snapshot && (
                    <details className="reader-snapshot">
                      <summary>Evidence recorded with the answer</summary>
                      <SourceMarkdown text={text(data.cited_snapshot.text)} />
                    </details>
                  )}
                  {data.content_type === "unavailable" ? (
                    <p role="status">
                      {data.detail || "Source content is unavailable."}
                    </p>
                  ) : data.content_type === "dataset" ? (
                    <div
                      className="reader-table"
                      tabIndex={0}
                      aria-label="Source rows"
                    >
                      <table>
                        <caption>
                          Actual source rows · each row retains its own source
                          version
                        </caption>
                        <thead>
                          <tr>
                            {columns.map((column) => (
                              <th key={column.name} scope="col">
                                {column.name.replaceAll("_", " ")}
                                {column.unit && <small>{column.unit}</small>}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {data.rows?.map((row, index) => (
                            <tr key={text(row.locator) + index}>
                              {columns.map((column) => (
                                <td key={column.name}>
                                  {text(object(row.values)[column.name])}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {!data.rows?.length && (
                        <p>No rows in this source page.</p>
                      )}
                    </div>
                  ) : (
                    <SourceMarkdown text={data.text} />
                  )}
                  {(history.length > 0 || data.has_more) && (
                    <div className="reader-pagination">
                      <button
                        disabled={!history.length}
                        onClick={() => {
                          setCursor(history[history.length - 1]);
                          setHistory(history.slice(0, -1));
                        }}
                      >
                        Previous source page
                      </button>
                      <span>Page {history.length + 1}</span>
                      <button
                        disabled={!data.has_more || !data.cursor}
                        onClick={() => {
                          setHistory([...history, cursor]);
                          setCursor(data.cursor!);
                        }}
                      >
                        Next source page
                      </button>
                    </div>
                  )}
                </>
              )}
              {tab === "Context" && (
                <>
                  <Context
                    value={{
                      ...data.context,
                      ...(productDetail.data
                        ? { product: productDetail.data }
                        : {}),
                    }}
                  />
                  <h3>Source provenance</h3>
                  <ul className="reader-refs">
                    {data.source_refs?.map((ref) => (
                      <li key={ref.asset_id + ref.locator}>
                        <strong>{ref.locator}</strong>
                        <span>{ref.asset_id}</span>
                        <code>{ref.version}</code>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {tab === "Relationships" && (
                <div className="reader-relationships">
                  <h3>Governing relationships</h3>
                  {data.paths?.length ? (
                    data.paths.map((path, index) => (
                      <div key={index} className="reader-path">
                        {Array.isArray(path.nodes) &&
                          path.nodes
                            .map((node) =>
                              text(
                                object(node).name || object(node).id || node,
                              ),
                            )
                            .join(" → ")}
                        {Array.isArray(path.edges) &&
                          path.edges.map((edge, edgeIndex) => {
                            const e = object(edge);
                            const source = text(e.source ?? e.subject),
                              target = text(e.target ?? e.object);
                            function openRelated(id: string) {
                              setRelated({ kind: "record", id });
                              setCursor("");
                              setHistory([]);
                              setTab("Content");
                            }
                            return (
                              <p key={edgeIndex}>
                                <button
                                  aria-label={"Open related node " + source}
                                  onClick={() => openRelated(source)}
                                >
                                  {text(e.source_name || source)}
                                </button>
                                {" → " + text(e.predicate) + " → "}
                                <button
                                  aria-label={"Open related node " + target}
                                  onClick={() => openRelated(target)}
                                >
                                  {text(e.target_name || target)}
                                </button>
                              </p>
                            );
                          })}
                      </div>
                    ))
                  ) : (
                    <p>
                      No asserted governing path was found in this bounded
                      source view.
                    </p>
                  )}
                  {concepts.length > 0 && (
                    <>
                      <h3>Related concepts</h3>
                      {concepts.map((concept) => (
                        <Link
                          key={text(concept)}
                          className="concept-chip"
                          href={
                            "/ontology?concept=" +
                            encodeURIComponent(text(concept))
                          }
                        >
                          {text(concept)}
                        </Link>
                      ))}
                    </>
                  )}
                </div>
              )}
            </>
          )
        )}
      </div>
    </Modal>
  );
}
