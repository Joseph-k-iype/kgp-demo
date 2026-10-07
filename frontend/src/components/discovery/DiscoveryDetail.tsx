"use client";
import { useState } from "react";
import { Database, FileText, Network, ArrowUpRight } from "lucide-react";
import { useData, RecordItem, Evidence } from "@/api/client";
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
            <h3>Underlying knowledge</h3>
            {product.data.assets?.map((item) => (
              <button
                key={item.id}
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
                  <small>{item.type}</small>
                </span>
                <ArrowUpRight size={15} />
              </button>
            ))}
            {product.data.gaps && product.data.gaps.length > 0 && (
              <>
                <h3>Coverage gaps</h3>
                {product.data.gaps.map((gap) => (
                  <p key={gap.id} className="detail-gap">
                    {gap.description}
                  </p>
                ))}
              </>
            )}
          </div>
        )}
      </Modal>
      {asset && <AssetDetail id={asset} onClose={() => setAsset("")} />}
    </>
  );
}
