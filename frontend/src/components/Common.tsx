"use client";
import { useEffect, useRef } from "react";
import {
  X,
  Database,
  FileText,
  Network,
  Box,
  Search,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";
import type { RecordItem } from "@/api/client";
export function PageHeading({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">ENTERPRISE KNOWLEDGE</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Badge({
  children,
  tone = "blue",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function AssetIcon({ type = "product" }: { type?: string }) {
  const Icon =
    type === "Document"
      ? FileText
      : type === "Metadata"
        ? Network
        : type === "Table"
          ? Database
          : Box;
  return type === "Document" || type === "Metadata" ? (
    <span className="asset-icon generated-icon">
      <img
        src={type === "Document" ? "/design/document.png" : "/design/graph.png"}
        alt=""
        width={43}
        height={43}
      />
    </span>
  ) : (
    <span className="asset-icon">
      <Icon size={22} />
    </span>
  );
}
export function Formats({
  items = ["SQL", "Document", "RDF", "Vector"],
}: {
  items?: string[];
}) {
  return (
    <div className="formats">
      {items.map((f) => (
        <Badge
          key={f}
          tone={
            f === "RDF"
              ? "teal"
              : f === "Vector"
                ? "violet"
                : f === "Document"
                  ? "neutral"
                  : "blue"
          }
        >
          {f === "SQL" ? (
            <Database size={11} />
          ) : f === "RDF" ? (
            <Network size={11} />
          ) : f === "Document" ? (
            <FileText size={11} />
          ) : (
            <Search size={11} />
          )}{" "}
          {f}
        </Badge>
      ))}
    </div>
  );
}
export function Loading({
  error = "",
  loading = true,
}: {
  error?: string;
  loading?: boolean;
}) {
  return (
    <div
      className={"state " + (error ? "error" : "")}
      role={error ? "alert" : "status"}
    >
      {error ? (
        <>
          <strong>Unable to load this view</strong>
          <p>{error}</p>
        </>
      ) : loading ? (
        <>
          <span className="loader" />
          <p>Loading enterprise knowledge…</p>
        </>
      ) : (
        <>
          <Search size={24} />
          <strong>No matching knowledge</strong>
          <p>Try another search or adjust your filters.</p>
        </>
      )}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement;
    ref.current?.focus();
    const bodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const focus = ref.current?.querySelectorAll<HTMLElement>(
          'button,input,select,a[href],textarea,[tabindex="0"]',
        );
        if (!focus?.length) return;
        const first = focus[0],
          last = focus[focus.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = bodyOverflow;
      before?.focus();
    };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={ref}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
export function Quality({ value = 100 }: { value?: number }) {
  return (
    <span className={"quality " + (value < 90 ? "warning" : "")}>
      <span className={"dot " + (value < 90 ? "amber" : "green")} />
      {value}% <span className="quality-label">quality</span>
    </span>
  );
}
export function DomainName({ id }: { id?: string | null }) {
  const names: Record<string, string> = {
    risk: "Risk and Compliance",
    legal: "Legal",
    technology: "Technology",
    product: "Product",
    operations: "Services and Operations",
    data: "Data and Information",
    finance: "Finance Treasury and Enterprise Tax",
    people: "People",
    "third-party": "Third Party and Support",
    strategy: "Strategy and Change",
    customer: "Customer and Counterparty",
  };
  return <>{id ? names[id] || id : "Enterprise"}</>;
}
export function DetailGrid({ record }: { record: RecordItem }) {
  return (
    <dl className="detail-grid">
      <div>
        <dt>Domain</dt>
        <dd>
          <DomainName id={record.domain_id} />
        </dd>
      </div>
      <div>
        <dt>Steward</dt>
        <dd>{record.steward || record.owner || "Enterprise stewardship"}</dd>
      </div>
      <div>
        <dt>Status</dt>
        <dd>
          <Badge tone={record.status === "Active" ? "teal" : "neutral"}>
            {record.status || "Registered"}
          </Badge>
        </dd>
      </div>
      <div>
        <dt>Classification</dt>
        <dd>{record.classification || "Internal"}</dd>
      </div>
    </dl>
  );
}
export function PanelHeading({
  title,
  action,
}: {
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="panel-heading">
      <h2>{title}</h2>
      {action}
    </div>
  );
}
