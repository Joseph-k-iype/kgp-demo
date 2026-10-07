"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  Layers,
  Database,
  Network,
  FolderKanban,
  Users,
  ArrowUpRight,
  CheckCircle2,
} from "lucide-react";
import { api, useData } from "@/api/client";
const ShaderSurface = dynamic(() => import("./ShaderSurface"), { ssr: false });
const Context = createContext({
  token: "atlas-session-admin",
  persona: "admin",
  role: "Administrator",
});
export const useSession = () => useContext(Context);
const people = {
  admin: ["Elena Vasquez", "Administrator"],
  analyst: ["James Morgan", "Analyst"],
  risk: ["Priya Shah", "Domain steward"],
  legal: ["Marcus Chen", "Delegate"],
} as const;
const workspace = [
  ["/domains", "Domains", Layers],
  ["/sources", "Sources", Database],
  ["/ontology", "Ontology explorer", Network],
  ["/projects", "Projects & gaps", FolderKanban],
  ["/roles", "Roles & access", Users],
] as const;
export function DotMark() {
  return (
    <span className="discovery-mark" aria-hidden="true">
      {Array.from({ length: 9 }, (_, i) => (
        <i key={i} />
      ))}
    </span>
  );
}
export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [persona, setPersona] = useState<keyof typeof people>("admin"),
    [menu, setMenu] = useState(false),
    [sessionError, setSessionError] = useState("");
  const navRef = useRef<HTMLDivElement>(null),
    trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const p = localStorage.getItem("atlas-persona");
    if (p && p in people) setPersona(p as keyof typeof people);
  }, []);
  useEffect(() => setMenu(false), [path]);
  useEffect(() => {
    if (!menu) return;
    function outside(e: PointerEvent) {
      if (!navRef.current?.contains(e.target as Node)) setMenu(false);
    }
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenu(false);
        trigger.current?.focus();
      }
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", key);
    };
  }, [menu]);
  const token = "atlas-session-" + persona;
  const liveScope = useData<{ role: string }>("/session/scope", token);
  const health = useData<{ services: Record<string, { status: string }> }>(
    menu ? "/health" : null,
    token,
  );
  async function switchPersona(p: keyof typeof people) {
    try {
      await api("/session", "", {
        method: "POST",
        body: JSON.stringify({ persona: p }),
      });
      localStorage.setItem("atlas-persona", p);
      setPersona(p);
      setSessionError("");
    } catch (e) {
      setSessionError((e as Error).message);
    }
  }
  return (
    <Context.Provider
      value={{
        token,
        persona,
        role: liveScope.data?.role || people[persona][1],
      }}
    >
      <div className="discovery-shell">
        {path === "/" && (
          <div className="home-texture">
            <ShaderSurface />
          </div>
        )}
        <header className="discovery-nav">
          <Link href="/" className="discovery-brand">
            <DotMark />
            <span>Knowledge Product Manager</span>
          </Link>
          <nav className="discovery-nav-actions" aria-label="Main navigation">
            <Link
              href="/catalog"
              className={
                "nav-catalog " + (path === "/catalog" ? "current" : "")
              }
            >
              <BookOpen size={17} />
              <span>Catalog</span>
            </Link>
            <div className="workspace-popover" ref={navRef}>
              <button
                ref={trigger}
                className="workspace-trigger"
                aria-expanded={menu}
                aria-controls="workspace-links"
                onClick={() => setMenu(!menu)}
              >
                Workspace <ChevronDown size={14} />
              </button>
              {menu && (
                <div id="workspace-links" className="workspace-links">
                  <small>MANAGE KNOWLEDGE</small>
                  {workspace.map(([url, label, Icon]) => (
                    <Link key={url} href={url} onClick={() => setMenu(false)}>
                      <Icon size={17} />
                      {label}
                    </Link>
                  ))}
                  <div className="workspace-connection">
                    <CheckCircle2 size={14} />
                    {health.data &&
                    Object.values(health.data.services).every(
                      (s) => s.status === "ready",
                    )
                      ? "All services connected"
                      : "Service readiness"}
                    <small>PostgreSQL · MinIO · RDF · OpenSearch</small>
                  </div>
                  <a
                    href="http://127.0.0.1:58123/docs"
                    target="_blank"
                    rel="noreferrer"
                  >
                    API & MCP connection <ArrowUpRight size={14} />
                  </a>
                </div>
              )}
            </div>
            <div className="discovery-persona">
              <span className="persona-circle" aria-hidden="true">
                {people[persona][0]
                  .split(" ")
                  .map((n) => n[0])
                  .join("")}
              </span>
              <select
                aria-label="Demo persona"
                value={persona}
                onChange={(e) =>
                  switchPersona(e.target.value as keyof typeof people)
                }
              >
                {Object.entries(people).map(([id, p]) => (
                  <option key={id} value={id}>
                    {p[0]}
                  </option>
                ))}
              </select>
            </div>
          </nav>
        </header>
        {sessionError && (
          <p role="alert" className="session-error">
            {sessionError}
          </p>
        )}
        <main
          className={
            path === "/" ? "discovery-home-main" : "content discovery-main"
          }
        >
          {children}
        </main>
        <footer className="discovery-footer">
          <span>Knowledge Product Manager</span>
          <span>Governed knowledge · Synthetic demo</span>
        </footer>
      </div>
    </Context.Provider>
  );
}
