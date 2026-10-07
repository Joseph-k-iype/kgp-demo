"use client";
import Link from "next/link";
import {
  Box,
  Layers,
  Database,
  ShieldAlert,
  ArrowUpRight,
  Sparkles,
  Network,
  ChevronRight,
} from "lucide-react";
import { useSession } from "@/components/Shell";
import { useData, RecordItem } from "@/api/client";
import {
  PageHeading,
  Loading,
  Badge,
  PanelHeading,
  Quality,
  AssetIcon,
} from "@/components/Common";
export default function Overview() {
  const { token } = useSession();
  const { data, error, loading } = useData<{
    counts: Record<string, number>;
    domains: RecordItem[];
    attention: RecordItem[];
    recent: RecordItem[];
    indexed: number;
  }>("/overview", token);
  if (loading || error)
    return (
      <>
        <PageHeading
          title="Knowledge overview"
          description="A connected view of your enterprise knowledge estate."
        />
        <Loading error={error} />
      </>
    );
  return (
    <>
      <PageHeading
        title="Your knowledge, connected."
        description="Discover what the enterprise knows, who governs it, and where the gaps remain."
        action={
          <Link className="btn btn-primary" href="/catalog">
            Explore catalog <ArrowUpRight size={14} />
          </Link>
        }
      />
      <div className="stats">
        {[
          ["Knowledge products", data?.counts.product, Box],
          ["Business domains", data?.counts.domain, Layers],
          ["Data & knowledge assets", data?.counts.asset, Database],
          ["Open coverage gaps", data?.counts.gap, ShieldAlert],
        ].map(([label, value, Icon]) => {
          const I = Icon as typeof Box;
          return (
            <div className="stat" key={String(label)}>
              <span className="stat-icon">
                <I size={21} />
              </span>
              <div>
                <div className="stat-label">{String(label)}</div>
                <div className="stat-value">{String(value)}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="two-col">
        <section className="panel">
          <PanelHeading
            title="Knowledge across the enterprise"
            action={<Badge tone="neutral">11 domains</Badge>}
          />
          {data?.domains.map((d) => (
            <Link
              href={"/catalog?domain_id=" + d.id}
              className="coverage-row"
              style={{ display: "block" }}
              key={d.id}
            >
              <div className="coverage-top">
                <strong style={{ fontWeight: 500 }}>{d.name}</strong>
                <span className="muted">
                  {d.product_count} products · {d.asset_count as number} assets{" "}
                  <ChevronRight size={12} />
                </span>
              </div>
              <div className="coverage-track">
                <span
                  style={{
                    width:
                      Math.min((Number(d.asset_count) / 15) * 100, 100) + "%",
                  }}
                />
              </div>
            </Link>
          ))}
          <div className="panel-body">
            <p className="metric-note">
              Asset distribution across the 150 seeded assets
            </p>
          </div>
        </section>
        <div>
          <section className="panel">
            <PanelHeading
              title="Needs your attention"
              action={
                <Link href="/projects" className="text-link">
                  View all <ArrowUpRight size={12} />
                </Link>
              }
            />
            {data?.attention.map((g) => (
              <Link href="/projects" key={g.id} className="attention-row">
                <span
                  className="mini-icon"
                  style={{ color: "#d19b3d", background: "#fffaf0" }}
                >
                  <ShieldAlert size={16} />
                </span>
                <div>
                  <h3>{g.name}</h3>
                  <p>{g.description}</p>
                  <div className="actions-row">
                    <Badge tone="amber">{g.coverage}% coverage</Badge>
                    <span className="muted" style={{ fontSize: 9 }}>
                      {g.quality_issues} quality issues
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </section>
          <section className="panel mcp-box">
            <div className="spaced">
              <h2>Ask your knowledge estate</h2>
              <Sparkles size={18} color="#0876f9" />
            </div>
            <p>
              Find structured records and supporting documents through
              ontology-guided, evidence-backed search.
            </p>
            <Link
              href="/search"
              className="btn btn-primary"
              style={{ marginTop: 8 }}
            >
              Start an agentic search <ArrowUpRight size={13} />
            </Link>
          </section>
          <section className="panel mcp-box">
            <div className="spaced">
              <h2>Connected by design</h2>
              <Network size={17} color="#099c92" />
            </div>
            <p>
              {data?.indexed} assets indexed with local embeddings. RDF
              relationships connect meaning, ownership, and source evidence.
            </p>
            <div className="formats">
              <Badge>PostgreSQL</Badge>
              <Badge tone="neutral">MinIO</Badge>
              <Badge tone="teal">RDF</Badge>
              <Badge tone="violet">OpenSearch</Badge>
            </div>
          </section>
        </div>
      </div>
      <section className="panel section-space">
        <PanelHeading
          title="Recently updated products"
          action={
            <Link href="/catalog" className="text-link">
              Browse catalog <ArrowUpRight size={12} />
            </Link>
          }
        />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>KNOWLEDGE PRODUCT</th>
                <th>STEWARD</th>
                <th>STATUS</th>
                <th>QUALITY</th>
                <th>ASSETS</th>
              </tr>
            </thead>
            <tbody>
              {data?.recent.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link
                      href={"/catalog?selected=" + p.id}
                      className="table-name"
                    >
                      <AssetIcon />
                      <strong>{p.name}</strong>
                    </Link>
                  </td>
                  <td>{p.steward}</td>
                  <td>
                    <Badge tone={p.status === "Active" ? "teal" : "neutral"}>
                      {p.status}
                    </Badge>
                  </td>
                  <td>
                    <Quality value={p.quality} />
                  </td>
                  <td>{p.asset_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
