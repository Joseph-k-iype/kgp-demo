"use client";
import Link from "next/link";
import { useState } from "react";
import { Layers, ArrowUpRight, User, Database, Box, Users } from "lucide-react";
import { useData, RecordItem } from "@/api/client";
import { useSession } from "@/components/Shell";
import { PageHeading, Loading, Badge, Modal } from "@/components/Common";
export default function Domains() {
  const { token } = useSession(),
    { data, error, loading } = useData<RecordItem[]>("/domains", token);
  const [selected, setSelected] = useState<RecordItem | null>(null);
  return (
    <>
      <PageHeading
        title="Business domains"
        description="Clear accountability for knowledge across the enterprise. Explore stewards, delegates, and subdomains."
        action={<Badge tone="neutral">{data?.length || "—"} domains</Badge>}
      />
      {loading || error ? (
        <Loading error={error} />
      ) : (
        <div className="three-col">
          {data?.map((d, i) => (
            <article className="panel domain-card" key={d.id}>
              <div className="domain-top">
                <span className="asset-icon" style={{ width: 34, height: 34 }}>
                  <Layers size={18} />
                </span>
                <span className="domain-number">
                  {String(i + 1).padStart(2, "0")} / ENTERPRISE
                </span>
              </div>
              <h2>{d.name}</h2>
              <p>{d.description}</p>
              <div className="concepts" style={{ marginBottom: 17 }}>
                {d.subdomains?.map((s) => (
                  <Badge key={s.id} tone="neutral">
                    {s.name}
                  </Badge>
                ))}
              </div>
              <div className="steward">
                <User size={13} />
                <span>
                  {d.steward}
                  <small style={{ display: "block", color: "#8da0b6" }}>
                    Domain steward
                  </small>
                </span>
                <button
                  className="btn btn-ghost"
                  onClick={() => setSelected(d)}
                  style={{ marginLeft: "auto" }}
                >
                  Details <ArrowUpRight size={12} />
                </button>
              </div>
              <Link
                className="domain-footer"
                href={"/catalog?domain_id=" + d.id}
              >
                <span>
                  <Box size={12} /> {d.product_count} products
                </span>
                <span>
                  <Database size={12} /> {d.asset_count as number} assets
                </span>
                <ArrowUpRight size={12} style={{ marginLeft: "auto" }} />
              </Link>
            </article>
          ))}
        </div>
      )}
      {selected && (
        <Modal title={selected.name} onClose={() => setSelected(null)}>
          <div className="modal-body">
            <p>{selected.description}</p>
            <div className="form-grid section-space">
              <div className="notice">
                <strong>Steward</strong>
                <p>{selected.steward}</p>
              </div>
              <div className="notice">
                <strong>Delegates</strong>
                {selected.delegates?.map((n) => (
                  <p key={n}>{n}</p>
                ))}
              </div>
            </div>
            <h3 className="section-space" style={{ marginBottom: 15 }}>
              Subdomains
            </h3>
            {selected.subdomains?.map((s) => (
              <div
                className="panel panel-body"
                style={{ marginBottom: 10 }}
                key={s.id}
              >
                <h3>{s.name}</h3>
                <p style={{ marginTop: 5 }}>{s.description}</p>
              </div>
            ))}
            <Link
              href={"/catalog?domain_id=" + selected.id}
              className="btn btn-primary section-space"
            >
              Explore domain knowledge <ArrowUpRight size={14} />
            </Link>
          </div>
        </Modal>
      )}
    </>
  );
}
