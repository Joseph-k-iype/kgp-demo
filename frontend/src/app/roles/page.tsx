"use client";
import { useState } from "react";
import { Users, ShieldCheck, Pencil, Lock, Check } from "lucide-react";
import { useData, api, CatalogPage, RecordItem } from "@/api/client";
import { useSession } from "@/components/Shell";
import {
  PageHeading,
  Loading,
  Badge,
  DomainName,
  Modal,
  PanelHeading,
} from "@/components/Common";
const roles = [
  "Administrator",
  "Domain steward",
  "Delegate",
  "Product owner",
  "Analyst",
  "Reviewer",
];
export default function Roles() {
  const { token, role } = useSession(),
    assignments = useData<CatalogPage>(
      "/catalog?kind=role&page_size=100",
      token,
    ),
    domains = useData<RecordItem[]>("/domains", token);
  const [editing, setEditing] = useState<RecordItem | null>(null),
    [newRole, setNewRole] = useState(""),
    [scope, setScope] = useState<string[]>([]),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(false);
  async function save() {
    if (!editing) return;
    try {
      await api("/records/role/" + editing.id, token, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole, domain_ids: scope }),
      });
      setEditing(null);
      assignments.reload();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <PageHeading
        title="Roles & access"
        description="Define accountability and access boundaries for products, assets, and agentic search."
        action={
          <Badge tone="teal">
            <ShieldCheck size={12} /> Scope enforced
          </Badge>
        }
      />
      <div className="notice" style={{ marginBottom: 24 }}>
        Demo identity simulation. The profile selector changes personas; all
        catalog, graph, evidence, and MCP access is checked by the backend.
      </div>
      <section className="panel">
        <PanelHeading
          title="Role assignments"
          action={
            <Badge tone="neutral">
              {assignments.data?.total || "—"} demo identities
            </Badge>
          }
        />
        {assignments.loading || assignments.error ? (
          <Loading error={assignments.error} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>PERSON</th>
                  <th>ROLE</th>
                  <th>DOMAIN SCOPE</th>
                  <th>PERMISSIONS</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {assignments.data?.items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <div className="table-name">
                        <span className="avatar">
                          {r.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </span>
                        <strong>{r.name}</strong>
                      </div>
                    </td>
                    <td>
                      <Badge
                        tone={
                          r.role === "Administrator"
                            ? "violet"
                            : r.role === "Analyst"
                              ? "neutral"
                              : "blue"
                        }
                      >
                        {r.role}
                      </Badge>
                    </td>
                    <td>
                      <div className="concepts">
                        {r.domain_ids?.length === 11 ? (
                          <Badge tone="neutral">All 11 business domains</Badge>
                        ) : (
                          r.domain_ids?.map((id) => (
                            <Badge key={id} tone="neutral">
                              <DomainName id={id} />
                            </Badge>
                          ))
                        )}
                      </div>
                    </td>
                    <td className="muted">
                      {r.role === "Administrator"
                        ? "Manage all metadata & roles"
                        : r.role === "Analyst" || r.role === "Reviewer"
                          ? "Browse, search & inspect evidence"
                          : "Edit within assigned scope"}
                    </td>
                    <td>
                      {role === "Administrator" && (
                        <button
                          className="icon-button"
                          aria-label={"Edit role for " + r.name}
                          onClick={() => {
                            setEditing(r);
                            setNewRole(r.role || "Analyst");
                            setScope(r.domain_ids || []);
                            setError("");
                          }}
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
        )}
      </section>
      <div className="three-col section-space">
        {roles.map((r) => (
          <div className="panel panel-body" key={r}>
            <div className="spaced">
              <h2>{r}</h2>
              {r === "Administrator" ? (
                <ShieldCheck size={17} color="#8355d8" />
              ) : (
                <Users size={17} color="#7599c2" />
              )}
            </div>
            <p style={{ fontSize: 11, marginTop: 10, lineHeight: 1.8 }}>
              {r === "Administrator"
                ? "Manage catalog metadata, role assignments, and the full enterprise scope."
                : r === "Domain steward"
                  ? "Accountable for domain knowledge quality, stewardship, and metadata."
                  : r === "Delegate"
                    ? "Maintain scoped metadata on behalf of the domain steward."
                    : r === "Product owner"
                      ? "Maintain metadata for knowledge products within the assigned scope."
                      : r === "Reviewer"
                        ? "Inspect governed products, source evidence, and quality findings."
                        : "Discover knowledge and run evidence-backed search within allowed domains."}
            </p>
          </div>
        ))}
      </div>
      <div
        className="notice section-space"
        style={{ display: "flex", alignItems: "center", gap: 10 }}
      >
        <Lock size={17} /> Scope changes invalidate previously retrieved search
        evidence. MCP callers use a server-configured identity and cannot select
        personas through tool arguments.
      </div>
      {editing && (
        <Modal
          title={"Role assignment · " + editing.name}
          onClose={() => setEditing(null)}
        >
          <div className="modal-body">
            <label style={{ display: "block", fontSize: 11 }}>
              Role
              <select
                aria-label="Assigned role"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                style={{ display: "block", width: "100%", marginTop: 7 }}
              >
                {roles.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </label>
            <h3 style={{ margin: "23px 0 13px" }}>Domain scope</h3>
            <div className="form-grid">
              {domains.data?.map((d) => (
                <label
                  key={d.id}
                  style={{ flexDirection: "row", alignItems: "center" }}
                >
                  <input
                    type="checkbox"
                    checked={scope.includes(d.id)}
                    onChange={(e) =>
                      setScope(
                        e.target.checked
                          ? [...scope, d.id]
                          : scope.filter((s) => s !== d.id),
                      )
                    }
                  />
                  {d.name}
                </label>
              ))}
            </div>
            {error && <div className="inline-error section-space">{error}</div>}
            <div className="form-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setEditing(null)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" onClick={save}>
                Save assignment
              </button>
            </div>
          </div>
        </Modal>
      )}
      {saved && (
        <div className="toast" role="status">
          Role assignment saved
        </div>
      )}
    </>
  );
}
