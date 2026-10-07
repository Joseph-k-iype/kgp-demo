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
export function prepareSearch(
  value: SearchSubmission,
  persona: string,
  mode: "llm" | "extractive" = "llm",
  force = false,
) {
  const query = value.query.trim(),
    key = searchKey(query, value.domainId, persona);
  const params = new URLSearchParams({ q: query });
  if (value.domainId) params.set("domain_id", value.domainId);
  try {
    const previous = JSON.parse(
      sessionStorage.getItem("kpm-search-intent") || "null",
    );
    if (
      !force &&
      previous?.key === key &&
      (previous.mode || "llm") === mode &&
      Date.now() - previous.submittedAt < 1000
    )
      return "/search?" + params;
  } catch {}
  const intent = {
    id: crypto.randomUUID(),
    query,
    domainId: value.domainId,
    persona,
    key,
    mode,
    submittedAt: Date.now(),
  };
  sessionStorage.setItem("kpm-search-intent", JSON.stringify(intent));
  let previous: string[] = [];
  try {
    const data = JSON.parse(
      localStorage.getItem("kpm-recent-" + persona) || "[]",
    );
    if (Array.isArray(data))
      previous = data.filter((q) => typeof q === "string");
  } catch {}
  localStorage.setItem(
    "kpm-recent-" + persona,
    JSON.stringify([query, ...previous.filter((q) => q !== query)].slice(0, 5)),
  );
  window.dispatchEvent(new Event("kpm-search-submitted"));
  return "/search?" + params;
}
