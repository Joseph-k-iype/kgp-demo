"use client";
import { useState } from "react";
import Link from "next/link";
import {
  FolderKanban,
  ShieldAlert,
  Pencil,
  ArrowUpRight,
  Search,
  DollarSign,
  Layers,
} from "lucide-react";
import { useData, api, CatalogPage, RecordItem } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  PageHeading,
  Loading,
  Badge,
  Modal,
  DomainName,
  PanelHeading,
} from "@/components/Common";
export default function Projects() {
  const { token, role } = useSession();
  const [tab, setTab] = useState("project"),
    [domain, setDomain] = useState(""),
    [editing, setEditing] = useState<RecordItem | null>(null),
    [form, setForm] = useState<Record<string, string>>({}),
    [saving, setSaving] = useState(false),
    [error, setError] = useState(""),
    [toast, setToast] = useState("");
  const projects = useData<CatalogPage>(
      "/catalog?kind=project&page_size=100" +
        (domain ? "&domain_id=" + domain : ""),
      token,
    ),
    gaps = useData<CatalogPage>(
      "/catalog?kind=gap&page_size=100" +
        (domain ? "&domain_id=" + domain : ""),
      token,
    ),
    domains = useData<RecordItem[]>("/domains", token);
  const editAllowed = [
    "Administrator",
    "Domain steward",
    "Delegate",
    "Product owner",
  ].includes(role);
  const money = (value: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  function edit(r: RecordItem) {
    setEditing(r);
    setForm({
      description: r.description || "",
      status: r.status || "Open",
      budget: String(r.budget || 0),
      sponsor: r.sponsor || "",
      owner: r.owner || "",
    });
    setError("");
  }
  async function save() {
    if (!editing) return;
    setSaving(true);
    try {
      const patch =
        editing.kind === "project"
          ? {
              status: form.status,
              budget: Number(form.budget),
              sponsor: form.sponsor,
              description: form.description,
            }
          : {
              status: form.status,
              description: form.description,
              owner: form.owner,
            };
      await api("/records/" + editing.kind + "/" + editing.id, token, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      setEditing(null);
      projects.reload();
      gaps.reload();
      setToast("Changes saved");
      setTimeout(() => setToast(""), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  const state = tab === "project" ? projects : gaps;
  return (
    <>
      <PageHeading
        title="Projects & knowledge gaps"
        description="Track product delivery, investment, and the missing evidence that needs attention."
      />
      <div className="stats">
        <div className="stat">
          <span className="stat-icon">
            <FolderKanban size={20} />
          </span>
          <div>
            <div className="stat-label">Knowledge projects</div>
            <div className="stat-value">{projects.data?.total || "—"}</div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">
            <DollarSign size={20} />
          </span>
          <div>
            <div className="stat-label">Portfolio budget · USD</div>
            <div className="stat-value" style={{ fontSize: 21 }}>
              {projects.data
                ? money(
                    projects.data.items.reduce(
                      (s, p) => s + (p.budget || 0),
                      0,
                    ),
                  )
                : "—"}
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">
            <ShieldAlert size={20} />
          </span>
          <div>
            <div className="stat-label">Open coverage gaps</div>
            <div className="stat-value">
              {gaps.data?.items.filter((g) => g.status === "Open").length ??
                "—"}
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">
            <Layers size={20} />
          </span>
          <div>
            <div className="stat-label">Quality issues linked</div>
            <div className="stat-value">
              {gaps.data?.items.reduce(
                (s, g) => s + (g.quality_issues || 0),
                0,
              ) ?? "—"}
            </div>
          </div>
        </div>
      </div>
      <div className="spaced">
        <div className="tab-nav" style={{ flex: 1 }}>
          <button
            className={tab === "project" ? "active" : ""}
            onClick={() => setTab("project")}
          >
            Delivery projects
          </button>
          <button
            className={tab === "gap" ? "active" : ""}
            onClick={() => setTab("gap")}
          >
            Coverage gaps
          </button>
        </div>
        <select
          aria-label="Project domain filter"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          style={{ fontSize: 11, marginBottom: 23 }}
        >
          <option value="">All domains</option>
          {domains.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>
      {state.loading || state.error ? (
        <Loading error={state.error} />
      ) : tab === "project" ? (
        <div className="panel table-wrap">
          <table>
            <thead>
              <tr>
                <th>KNOWLEDGE PRODUCT / PROJECT</th>
                <th>DOMAIN</th>
                <th>SPONSOR</th>
                <th>BUDGET · USD</th>
                <th>STATUS</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {projects.data?.items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link
                      href={
                        "/catalog?domain_id=" +
                        p.domain_id +
                        "&selected=" +
                        p.product_id
                      }
                    >
                      <strong>{p.knowledge_product_name}</strong>
                      <p style={{ fontSize: 10, marginTop: 4 }}>{p.name}</p>
                    </Link>
                  </td>
                  <td>
                    <DomainName id={p.domain_id} />
                    <p style={{ fontSize: 9, marginTop: 3 }}>
                      {p.subdomain_id as string}
                    </p>
                  </td>
                  <td>{p.sponsor}</td>
                  <td className="oneline">{money(p.budget || 0)}</td>
                  <td>
                    <Badge
                      tone={
                        p.status === "Completed"
                          ? "teal"
                          : p.status === "In progress"
                            ? "blue"
                            : "neutral"
                      }
                    >
                      {p.status}
                    </Badge>
                  </td>
                  <td>
                    {editAllowed && (
                      <button
                        className="icon-button"
                        onClick={() => edit(p)}
                        aria-label={"Edit " + p.name}
                      >
                        <Pencil size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="three-col">
          {gaps.data?.items.map((g) => (
            <article className="panel panel-body" key={g.id}>
              <div className="spaced">
                <Badge tone={g.status === "Resolved" ? "teal" : "amber"}>
                  {g.status}
                </Badge>
                {editAllowed && (
                  <button
                    className="icon-button"
                    aria-label={"Edit " + g.name}
                    onClick={() => edit(g)}
                  >
                    <Pencil size={14} />
                  </button>
                )}
              </div>
              <h2 style={{ marginTop: 15 }}>{g.name}</h2>
              <p style={{ fontSize: 11, margin: "9px 0 17px" }}>
                {g.description}
              </p>
              <div className="spaced small-text">
                <span>Evidence coverage</span>
                <strong>{g.coverage}%</strong>
              </div>
              <div className="coverage-track">
                <span style={{ width: g.coverage + "%" }} />
              </div>
              <p className="metric-note">
                {g.covered} of {g.required} · {g.coverage_basis}
              </p>
              <div className="spaced" style={{ margin: "16px 0" }}>
                <span className="small-text muted">
                  {g.quality_issues} quality issues
                </span>
                <Link
                  href={"/catalog?domain_id=" + g.domain_id}
                  className="text-link"
                >
                  Explore assets <ArrowUpRight size={12} />
                </Link>
              </div>
              <div className="concepts">
                {g.tags?.map((t) => (
                  <Badge key={t} tone="neutral">
                    {t}
                  </Badge>
                ))}
              </div>
              <div
                style={{
                  borderTop: "1px solid #edf1f6",
                  paddingTop: 15,
                  marginTop: 15,
                  fontSize: 10,
                }}
              >
                <span className="muted">Remediation owner</span>
                <p style={{ marginTop: 4, color: "#315477" }}>{g.owner}</p>
              </div>
            </article>
          ))}
        </div>
      )}
      {!editAllowed && (
        <div className="notice section-space">
          Your demo role has read access. Switch to a domain steward or
          administrator to edit project and gap metadata.
        </div>
      )}
      {editing && (
        <Modal title={"Edit " + editing.name} onClose={() => setEditing(null)}>
          <div className="modal-body">
            <div className="form-grid">
              <label>
                Status
                <select
                  aria-label="Project status"
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  {(editing.kind === "project"
                    ? ["Planned", "In progress", "Completed"]
                    : ["Open", "Resolved"]
                  ).map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              {editing.kind === "project" ? (
                <>
                  <label>
                    Budget · USD
                    <input
                      aria-label="Project budget"
                      type="number"
                      min="0"
                      value={form.budget}
                      onChange={(e) =>
                        setForm({ ...form, budget: e.target.value })
                      }
                    />
                  </label>
                  <label className="full">
                    Sponsor
                    <input
                      value={form.sponsor}
                      onChange={(e) =>
                        setForm({ ...form, sponsor: e.target.value })
                      }
                    />
                  </label>
                </>
              ) : (
                <label>
                  Remediation owner
                  <input
                    value={form.owner}
                    onChange={(e) =>
                      setForm({ ...form, owner: e.target.value })
                    }
                  />
                </label>
              )}
              <label className="full">
                Description
                <textarea
                  rows={4}
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                />
              </label>
            </div>
            {error && <div className="inline-error section-space">{error}</div>}
            <div className="form-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setEditing(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={save}
                disabled={saving}
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        </Modal>
      )}
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </>
  );
}
