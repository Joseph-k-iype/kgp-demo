"use client";
import Link from "next/link";
import { useState } from "react";
import { Database, FileText, Network, ArrowUpRight } from "lucide-react";
import { useData, RecordItem, Evidence, CatalogPage } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  Modal,
  Loading,
  DomainName,
  Formats,
  Quality,
} from "@/components/Common";
import AssetDetail from "@/components/AssetDetail";
export function EvidenceDetail({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const { token } = useSession();
  const evidence = useData<Evidence>(
    "/evidence/" + encodeURIComponent(id),
    token,
  );
  return (
    <Modal title={evidence.data?.name || "Source evidence"} onClose={onClose}>
      {!evidence.data ? (
        <Loading error={evidence.error} />
      ) : (
        <div className="evidence-detail">
          <div className="evidence-label">
            <DomainName id={evidence.data.domain_id} />
            <span>{evidence.data.provenance.type}</span>
          </div>
          <p className="evidence-excerpt">{evidence.data.text}</p>
          <dl>
            <dt>Original source</dt>
            <dd>{evidence.data.provenance.location}</dd>
            {evidence.data.provenance.row_id && (
              <>
                <dt>Row identifier</dt>
                <dd>{evidence.data.provenance.row_id}</dd>
              </>
            )}
            {evidence.data.provenance.object_key && (
              <>
                <dt>Object</dt>
                <dd>{evidence.data.provenance.object_key}</dd>
              </>
            )}
            {evidence.data.provenance.start != null && (
              <>
                <dt>Document offset</dt>
                <dd>
                  {evidence.data.provenance.start}–
                  {evidence.data.provenance.end}
                </dd>
              </>
            )}
          </dl>
        </div>
      )}
    </Modal>
  );
}
export default function DiscoveryDetail({
  id,
  kind,
  onClose,
}: {
  id: string;
  kind: "product" | "asset";
  onClose: () => void;
}) {
  const { token } = useSession();
  const product = useData<RecordItem>(
    kind === "product" ? "/products/" + encodeURIComponent(id) : null,
    token,
  );
  const [asset, setAsset] = useState("");
  const [tab, setTab] = useState("Overview");
  const gaps = useData<CatalogPage>(
    tab === "Quality" && product.data
      ? "/catalog?kind=gap&page_size=100&domain_id=" + product.data.domain_id
      : null,
    token,
  );
  if (kind === "asset") return <AssetDetail id={id} onClose={onClose} />;
  return (
    <>
      <Modal
        title={product.data?.name || "Knowledge product"}
        onClose={onClose}
      >
        {!product.data ? (
          <Loading error={product.error} />
        ) : (
          <div className="product-discovery-detail">
            <p>{product.data.description}</p>
            <div className="detail-context">
              <span>
                <DomainName id={product.data.domain_id} />
              </span>
              <span>{product.data.steward}</span>
              <Quality value={product.data.quality} />
            </div>
            <Formats items={product.data.formats} />
            <div
              className="product-tabs"
              role="tablist"
              aria-label="Product details"
            >
              {["Overview", "Assets", "Ontology", "Quality", "Projects"].map(
                (name) => (
                  <button
                    key={name}
                    role="tab"
                    aria-selected={tab === name}
                    aria-controls="product-tab-content"
                    onClick={() => setTab(name)}
                  >
                    {name}
                  </button>
                ),
              )}
            </div>
            <div id="product-tab-content" role="tabpanel" aria-label={tab}>
              {tab === "Overview" && (
                <dl className="detail-grid">
                  <div>
                    <dt>Status</dt>
                    <dd>{product.data.status}</dd>
                  </div>
                  <div>
                    <dt>Classification</dt>
                    <dd>{product.data.classification}</dd>
                  </div>
                  <div>
                    <dt>Delegates</dt>
                    <dd>
                      {product.data.delegates?.join(", ") ||
                        "No delegates assigned"}
                    </dd>
                  </div>
                  <div>
                    <dt>Tags</dt>
                    <dd>{product.data.tags?.join(" · ")}</dd>
                  </div>
                </dl>
              )}
              {tab === "Assets" && (
                <>
                  <h3>Underlying knowledge</h3>
                  {product.data.assets?.map((item) => (
                    <button
                      key={item.id}
                      aria-label={item.name}
                      className="detail-source"
                      onClick={() => setAsset(item.id)}
                    >
                      {item.type === "Document" ? (
                        <FileText size={17} />
                      ) : item.type === "Metadata" ? (
                        <Network size={17} />
                      ) : (
                        <Database size={17} />
                      )}
                      <span>
                        {item.name}
                        <small>
                          {item.type} ·{" "}
                          {item.indexing_state === "ready"
                            ? "Indexed"
                            : "Index pending"}
                        </small>
                      </span>
                      <ArrowUpRight size={15} />
                    </button>
                  ))}
                </>
              )}
              {tab === "Ontology" && (
                <>
                  <h3>Governed concepts</h3>
                  <p>
                    Explore the RDF relationships governing this product and its
                    underlying assets.
                  </p>
                  <div className="concepts">
                    {product.data.concepts?.map((concept) => (
                      <Link
                        key={concept}
                        className="concept-chip"
                        href={
                          "/ontology?concept=" + encodeURIComponent(concept)
                        }
                      >
                        {concept}
                      </Link>
                    ))}
                  </div>
                </>
              )}
              {tab === "Quality" && (
                <>
                  <h3>Knowledge quality</h3>
                  <p>
                    Synthetic quality score · inspect underlying assets for
                    individual issues.
                  </p>
                  {gaps.loading || gaps.error ? (
                    <Loading error={gaps.error} />
                  ) : (
                    gaps.data?.items
                      .filter((gap) => gap.product_id === id)
                      .map((gap) => (
                        <div className="detail-gap" key={gap.id}>
                          <h4>{gap.name}</h4>
                          <p>{gap.description}</p>
                          <p>
                            {gap.coverage}% coverage · {gap.quality_issues} data
                            quality issues
                          </p>
                          <small>{gap.coverage_basis}</small>
                        </div>
                      ))
                  )}
                </>
              )}
              {tab === "Projects" && (
                <>
                  <h3>Related projects</h3>
                  {product.data.projects?.length ? (
                    product.data.projects.map((project) => (
                      <div className="detail-gap" key={project.id}>
                        <h4>{project.name}</h4>
                        <p>{project.description}</p>
                        <p>
                          {project.status} · Sponsor: {project.sponsor}
                        </p>
                        <p>
                          Budget: {project.currency || "USD"}{" "}
                          {project.budget?.toLocaleString()}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p>No projects linked.</p>
                  )}
                  <Link href="/projects" className="text-link">
                    Manage projects <ArrowUpRight size={14} />
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </Modal>
      {asset && <AssetDetail id={asset} onClose={() => setAsset("")} />}
    </>
  );
}
