import type { components } from "./generated";
import type { SearchSubmission } from "@/components/discovery/SearchBox";
export type DiscoveryItem = components["schemas"]["DiscoveryItem"];
export type DiscoveryPage = components["schemas"]["DiscoveryPage"];
export function searchKey(
  query: string,
  domainId: string | null,
  persona: string,
) {
  return JSON.stringify([persona, query.trim(), domainId || null]);
}
export function prepareSearch(value: SearchSubmission, persona: string) {
  const query = value.query.trim();
  const intent = {
    id: crypto.randomUUID(),
    query,
    domainId: value.domainId,
    persona,
    key: searchKey(query, value.domainId, persona),
  };
  sessionStorage.setItem("kpm-search-intent", JSON.stringify(intent));
  let previous: string[] = [];
  try {
    previous = JSON.parse(
      localStorage.getItem("kpm-recent-" + persona) || "[]",
    );
  } catch {}
  const recent = [
    query,
    ...previous.filter((q) => typeof q === "string" && q !== query),
  ].slice(0, 5);
  localStorage.setItem("kpm-recent-" + persona, JSON.stringify(recent));
  const params = new URLSearchParams({ q: query });
  if (value.domainId) params.set("domain_id", value.domainId);
  return "/search?" + params;
}
