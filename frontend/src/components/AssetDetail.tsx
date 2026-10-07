"use client";
import Link from "next/link";
import { useState } from "react";
import { Database, FileText, ArrowUpRight } from "lucide-react";
import { useSession } from "./Shell";
import { useData, api, RecordItem } from "@/api/client";
import { Modal, Loading, DetailGrid, Formats, Badge, Quality } from "./Common";
export default function AssetDetail({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const { token } = useSession();
  const { data, error, loading } = useData<RecordItem>("/assets/" + id, token);
  const [preview, setPreview] = useState<{
      text?: string;
      rows?: Record<string, unknown>[];
    } | null>(null),
    [previewError, setPreviewError] = useState(""),
    [busy, setBusy] = useState(false);
  async function loadPreview() {
    if (!data) return;
    setBusy(true);
    setPreviewError("");
    try {
      if (data.type === "Document")
        setPreview(await api("/assets/" + id + "/preview", token));
      else setPreview({ rows: await api("/assets/" + id + "/rows", token) });
    } catch (e) {
      setPreviewError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={data?.name || "Asset details"} onClose={onClose}>
      {loading || error ? (
        <Loading error={error} />
      ) : (
        data && (
          <div className="modal-body">
            <div className="spaced">
              <Formats
                items={[
                  data.type === "Document" ? "Document" : "SQL",
                  "RDF",
                  "Vector",
                ]}
              />
              <Quality value={data.quality} />
            </div>
            <p style={{ margin: "16px 0 20px" }}>{data.description}</p>
            <DetailGrid record={data} />
            <div className="section-space panel">
              <div className="panel-heading">
                <h2>Source & provenance</h2>
                <Badge tone="teal">{data.source?.type}</Badge>
              </div>
              <div className="panel-body">
                <h3>{data.source?.name}</h3>
                <p className="source-location" style={{ margin: "8px 0 15px" }}>
                  {data.storage_location}
                </p>
                <div className="spaced">
                  <span className="small-text muted">
                    {data.source?.system_of_record
                      ? "System of record"
                      : "Supporting evidence"}{" "}
                    · Synthetic data
                  </span>
                  <button
                    className="btn btn-primary"
                    onClick={loadPreview}
                    disabled={busy}
                  >
                    {data.type === "Document" ? (
                      <FileText size={14} />
                    ) : (
                      <Database size={14} />
                    )}{" "}
                    {busy ? "Loading…" : "Preview source"}
                  </button>
                </div>
              </div>
            </div>
            {previewError && (
              <div className="inline-error section-space">{previewError}</div>
            )}
            {preview && (
              <div className="section-space">
                <h3 style={{ marginBottom: 12 }}>Original source preview</h3>
                {preview.text ? (
                  <pre className="source-code">{preview.text}</pre>
                ) : (
                  preview.rows && (
                    <div className="table-wrap panel">
                      <table>
                        <thead>
                          <tr>
                            {Object.keys(preview.rows[0] || {}).map((k) => (
                              <th key={k}>{k.replaceAll("_", " ")}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {preview.rows.map((row, i) => (
                            <tr key={i}>
                              {Object.values(row).map((v, j) => (
                                <td key={j}>{String(v)}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
              </div>
            )}
            <div className="section-space">
              <h3 style={{ marginBottom: 12 }}>Ontology & indexing</h3>
              <div className="spaced">
                <div className="concepts">
                  {data.concepts?.map((c) => (
                    <Link
                      className="concept-chip"
                      href={"/ontology?concept=" + encodeURIComponent(c)}
                      key={c}
                    >
                      {c}
                      <ArrowUpRight size={11} />
                    </Link>
                  ))}
                </div>
                <Badge
                  tone={data.indexing_state === "ready" ? "teal" : "amber"}
                >
                  {data.indexing_state === "ready"
                    ? "Vector index ready"
                    : data.indexing_state}
                </Badge>
              </div>
            </div>
            {data.issues?.length ? (
              <div className="notice amber section-space">
                <strong>{data.issues.length} data quality issues</strong>
                {data.issues.map((i) => (
                  <p key={i.id}>
                    {i.name} · {i.status}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        )
      )}
    </Modal>
  );
}
