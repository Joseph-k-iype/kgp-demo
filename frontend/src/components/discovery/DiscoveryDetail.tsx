"use client";
import { useData, Evidence } from "@/api/client";
import { useSession } from "@/components/Shell";
import { Modal, Loading, DomainName } from "@/components/Common";
import ContentViewer from "./ContentViewer";
export function EvidenceDetail({
  id,
  onClose,
  runId,
  quote,
}: {
  id: string;
  runId?: string;
  quote?: string;
  onClose: () => void;
}) {
  const { token } = useSession();
  const evidence = useData<Evidence>(
    "/evidence/" +
      encodeURIComponent(id) +
      (runId ? "?run_id=" + encodeURIComponent(runId) : ""),
    token,
  );
  if (evidence.data?.source_ref)
    return (
      <ContentViewer
        handle={{
          kind: "asset",
          id: evidence.data.source_ref.asset_id,
          locator: evidence.data.source_ref.locator,
          version: evidence.data.source_ref.version,
          run_id: runId,
          evidence_id: id,
        }}
        quote={quote || evidence.data.text}
        onClose={onClose}
      />
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
  locator,
  version,
  preferredAsset,
}: {
  id: string;
  kind: "product" | "asset";
  onClose: () => void;
  locator?: string;
  version?: string;
  preferredAsset?: string;
}) {
  return (
    <ContentViewer
      handle={{ kind, id, locator, version }}
      preferredAsset={preferredAsset}
      onClose={onClose}
    />
  );
}
