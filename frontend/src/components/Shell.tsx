"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
const ShaderSurface = dynamic(() => import("./ShaderSurface"), { ssr: false });
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import {
  Box,
  LayoutDashboard,
  BookOpen,
  Layers,
  Database,
  Network,
  Sparkles,
  FolderKanban,
  Users,
  Search,
  ChevronDown,
  Menu,
  X,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";
import { api, useData } from "@/api/client";
const Context = createContext({
  token: "atlas-session-admin",
  persona: "admin",
  role: "Administrator",
});
export const useSession = () => useContext(Context);
const nav = [
  ["/", "Overview", LayoutDashboard],
  ["/catalog", "Catalog", BookOpen],
  ["/domains", "Domains", Layers],
  ["/sources", "Sources", Database],
  ["/ontology", "Ontology explorer", Network],
  ["/search", "Agentic search", Sparkles],
  ["/projects", "Projects & gaps", FolderKanban],
  ["/roles", "Roles & access", Users],
] as const;
const people = {
  admin: ["Elena Vasquez", "Administrator"],
  analyst: ["James Morgan", "Analyst"],
  risk: ["Priya Shah", "Domain steward"],
  legal: ["Marcus Chen", "Delegate"],
} as const;
export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname(),
    router = useRouter();
  const [persona, setPersona] = useState<keyof typeof people>("admin"),
    [menu, setMenu] = useState(false),
    [q, setQ] = useState("");
  useEffect(() => {
    const p = localStorage.getItem("atlas-persona");
    if (p && p in people) setPersona(p as keyof typeof people);
  }, []);
  const token = "atlas-session-" + persona;
  const liveScope = useData<{ role: string }>("/session/scope", token);
  const health = useData<{
    services: Record<string, { status: string }>;
    llm: { configured: boolean; model: string };
  }>("/health", token);
  async function switchPersona(p: keyof typeof people) {
    await api("/session", "", {
      method: "POST",
      body: JSON.stringify({ persona: p }),
    });
    localStorage.setItem("atlas-persona", p);
    setPersona(p);
  }
  const current = nav.find((n) => n[0] === path)?.[1] || "Catalog";
  const healthy =
    health.data &&
    Object.values(health.data.services).every((s) => s.status === "ready");
  return (
    <Context.Provider
      value={{
        token,
        persona,
        role: liveScope.data?.role || people[persona][1],
      }}
    >
      <div className="app-shell">
        <ShaderSurface />
        <aside className={"sidebar " + (menu ? "open" : "")}>
          <Link href="/" className="brand">
            <span className="brand-symbol">
              <span className="dot-mark">
                {Array.from({ length: 9 }, (_, i) => (
                  <i key={i} />
                ))}
              </span>
            </span>
            <span className="brand-name">
              Knowledge
              <br />
              Product Manager
            </span>
          </Link>
          <button
            className="mobile-close icon-button"
            onClick={() => setMenu(false)}
            aria-label="Close navigation"
          >
            <X />
          </button>
          <div className="workspace">
            <span className="workspace-icon">E</span>
            <div>
              Enterprise workspace<small>Knowledge intelligence</small>
            </div>
            <ChevronDown size={14} />
          </div>
          <div className="nav-label">WORKSPACE</div>
          <nav>
            {nav.map(([url, label, Icon]) => (
              <Link
                key={url}
                href={url}
                className={path === url ? "nav-link active" : "nav-link"}
                onClick={() => setMenu(false)}
              >
                <Icon size={19} />
                <span>{label}</span>
                {url === "/search" && <span className="nav-pill">AI</span>}
              </Link>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="system-state">
              <span className={"dot " + (healthy ? "green" : "amber")} />
              {healthy ? "All services connected" : "Checking services"}
            </div>
            <small>PostgreSQL · MinIO · RDF · OpenSearch</small>
            <a
              href="http://127.0.0.1:58123/docs"
              target="_blank"
              rel="noreferrer"
              className="api-link"
            >
              API & MCP documentation <ArrowUpRight size={14} />
            </a>
            <div className="demo-note">Synthetic data · Local demo</div>
          </div>
        </aside>
        <div className="workspace-body">
          <header className="topbar">
            <button
              className="mobile-menu icon-button"
              onClick={() => setMenu(true)}
              aria-label="Open navigation"
            >
              <Menu />
            </button>
            <div className="breadcrumb">
              Enterprise <span>/</span>
              <strong>{current}</strong>
            </div>
            <form
              className="global-search"
              onSubmit={(e) => {
                e.preventDefault();
                router.push("/catalog?text=" + encodeURIComponent(q));
              }}
            >
              <Search size={16} />
              <input
                aria-label="Global catalog search"
                placeholder="Search products, assets, or knowledge…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <kbd>↵</kbd>
            </form>
            <span className="governed-label">
              <ShieldCheck size={15} /> Governed workspace
            </span>
            <div className="profile">
              <span className="avatar">
                {people[persona][0]
                  .split(" ")
                  .map((n) => n[0])
                  .join("")}
              </span>
              <div>
                <select
                  aria-label="Demo persona"
                  value={persona}
                  onChange={(e) =>
                    switchPersona(e.target.value as keyof typeof people)
                  }
                >
                  {Object.entries(people).map(([id, [name]]) => (
                    <option key={id} value={id}>
                      {name}
                    </option>
                  ))}
                </select>
                <small>{people[persona][1]} · Demo persona</small>
              </div>
            </div>
          </header>
          <main key={persona}>{children}</main>
        </div>
      </div>
    </Context.Provider>
  );
}
