"use client";
import { useState } from "react";
import {
  Database,
  FileText,
  Search,
  ArrowUpRight,
  RefreshCw,
} from "lucide-react";
import { useData, CatalogPage, RecordItem } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  PageHeading,
  Loading,
  Badge,
  Modal,
  DomainName,
  PanelHeading,
} from "@/components/Common";
import AssetDetail from "@/components/AssetDetail";
export default function Sources() {
  const { token } = useSession();
  const [type, setType] = useState(""),
    [selected, setSelected] = useState<RecordItem | null>(null),
    [asset, setAsset] = useState("");
  const sources = useData<CatalogPage>(
    "/catalog?kind=source&page_size=100",
    token,
  );
  const assets = useData<CatalogPage>(
    selected
      ? "/catalog?kind=asset&source_id=" + selected.id + "&page_size=100"
      : null,
    token,
  );
  return (
    <>
      <PageHeading
        title="Source inventory"
        description="Know where your knowledge comes from. Inspect systems of record, object stores, and their underlying assets."
        action={
          <button className="btn btn-secondary" onClick={sources.reload}>
            <RefreshCw size={13} /> Refresh inventory
          </button>
        }
      />
      <div className="stats">
        <div className="stat">
          <span className="stat-icon">
            <Database size={20} />
          </span>
          <div>
            <div className="stat-label">PostgreSQL sources</div>
            <div className="stat-value">
              {sources.data?.items.filter((s) => s.type === "PostgreSQL")
                .length || "—"}
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">
            <FileText size={20} />
          </span>
          <div>
            <div className="stat-label">MinIO stores</div>
            <div className="stat-value">
              {sources.data?.items.filter((s) => s.type === "MinIO").length ||
                "—"}
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">
            <Database size={20} />
          </span>
          <div>
            <div className="stat-label">Systems of record</div>
            <div className="stat-value">
              {sources.data?.items.filter((s) => s.system_of_record).length ||
                "—"}
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">
            <Search size={20} />
          </span>
          <div>
            <div className="stat-label">Source status</div>
            <div className="stat-value" style={{ fontSize: 16 }}>
              Connected
            </div>
            <div className="stat-foot">Local demo services</div>
          </div>
        </div>
      </div>
      <div className="tab-nav">
        {["", "PostgreSQL", "MinIO"].map((t) => (
          <button
            key={t}
            className={type === t ? "active" : ""}
            onClick={() => setType(t)}
          >
            {t || "All sources"}
          </button>
        ))}
      </div>
      <div className="panel">
        {sources.loading || sources.error ? (
          <Loading error={sources.error} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SOURCE</th>
                  <th>DOMAIN</th>
                  <th>TYPE</th>
                  <th>SYSTEM OF RECORD</th>
                  <th>STATUS</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {sources.data?.items
                  .filter((s) => !type || s.type === type)
                  .map((s) => (
                    <tr
                      className="clickable"
                      key={s.id}
                      onClick={() => setSelected(s)}
                    >
                      <td>
                        <div className="table-name">
                          <span className="mini-icon">
                            {s.type === "MinIO" ? (
                              <FileText size={17} />
                            ) : (
                              <Database size={17} />
                            )}
                          </span>
                          <div>
                            <button onClick={() => setSelected(s)}>
                              <strong>{s.name}</strong>
                            </button>
                            <p className="source-location">
                              {s.storage_location}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td>
                        <DomainName id={s.domain_id} />
                      </td>
                      <td>
                        <Badge tone={s.type === "MinIO" ? "violet" : "blue"}>
                          {s.type}
                        </Badge>
                      </td>
                      <td>
                        {s.system_of_record
                          ? "Yes"
                          : "No · Supporting evidence"}
                      </td>
                      <td>
                        <Badge tone="teal">{s.connection_state}</Badge>
                      </td>
                      <td>
                        <ArrowUpRight size={14} color="#7699c0" />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {selected && (
        <Modal title={selected.name} onClose={() => setSelected(null)}>
          <div className="modal-body">
            <div className="spaced">
              <Badge>{selected.type}</Badge>
              <Badge tone="teal">{selected.connection_state}</Badge>
            </div>
            <p style={{ margin: "16px 0" }}>{selected.description}</p>
            <pre className="source-code">{selected.storage_location}</pre>
            <div className="section-space">
              <h3 style={{ marginBottom: 12 }}>Underlying assets</h3>
              {assets.loading ? (
                <Loading />
              ) : assets.error ? (
                <Loading error={assets.error} />
              ) : (
                assets.data?.items.map((a) => (
                  <button
                    key={a.id}
                    className="asset-link"
                    onClick={() => {
                      setSelected(null);
                      setAsset(a.id);
                    }}
                  >
                    <span>{a.name}</span>
                    <Badge tone="neutral">{a.type}</Badge>
                    <ArrowUpRight size={12} />
                  </button>
                ))
              )}
            </div>
          </div>
        </Modal>
      )}
      {asset && <AssetDetail id={asset} onClose={() => setAsset("")} />}
    </>
  );
}
