"use client";
import { useEffect, useState } from "react";
import type { components } from "./generated";
export type RecordItem = components["schemas"]["CatalogRecord"] & {
  type?: string;
  steward?: string;
  delegates?: string[];
  quality?: number;
  status?: string;
  tags?: string[];
  concepts?: string[];
  formats?: string[];
  asset_count?: number;
  indexing_state?: string;
  source_id?: string;
  classification?: string;
  storage_location?: string;
  system_of_record?: boolean;
  connection_state?: string;
  subdomains?: RecordItem[];
  product_count?: number;
  product_id?: string;
  knowledge_product_name?: string;
  sponsor?: string;
  budget?: number;
  currency?: string;
  coverage?: number;
  covered?: number;
  required?: number;
  coverage_basis?: string;
  quality_issues?: number;
  owner?: string;
  role?: string;
  domain_ids?: string[];
  assets?: RecordItem[];
  projects?: RecordItem[];
  gaps?: RecordItem[];
  source?: RecordItem;
  issues?: RecordItem[];
};
export type CatalogPage = {
  items: RecordItem[];
  total: number;
  page: number;
  page_size: number;
};
export type Evidence = {
  id: string;
  asset_id: string;
  domain_id: string;
  name: string;
  text: string;
  provenance: {
    type: string;
    location: string;
    row_id?: string;
    object_key?: string;
    start?: number;
    end?: number;
  };
};
export type GraphData = {
  nodes: { id: string; name: string; iri: string; kind: string }[];
  edges: { source: string; target: string; label: string }[];
  root?: string;
  truncated?: boolean;
};
export type Run = {
  run_id: string;
  query: string;
  status: string;
  mode: string;
  statements: { text: string; evidence_ids: string[] }[];
  evidence: Evidence[];
  gaps: string[];
  events: {
    sequence: number;
    stage: string;
    status: string;
    summary: string;
  }[];
  graph: GraphData;
  error?: string;
  uncertainty?: string;
};
export async function api<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + token,
      ...options.headers,
    },
  });
  const body = await response.json();
  if (!response.ok)
    throw new Error(body.detail || body.error || "Request failed");
  return body as T;
}
export function useData<T>(path: string | null, token: string) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    if (!path) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api<T>(path, token)
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, token, revision]);
  return { data, error, loading, reload: () => setRevision((n) => n + 1) };
}
export async function streamRun(
  id: string,
  token: string,
  onEvent: (event: Run["events"][number]) => void,
  onResult: (run: Run) => void,
  signal: AbortSignal,
) {
  const response = await fetch("/api/search/runs/" + id + "/events", {
    headers: { Authorization: "Bearer " + token },
    signal,
  });
  if (!response.ok || !response.body)
    throw new Error("Search stream unavailable");
  const reader = response.body.getReader(),
    decoder = new TextDecoder();
  let pending = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    pending += decoder.decode(value, { stream: true });
    let split;
    while ((split = pending.indexOf("\n\n")) >= 0) {
      const packet = pending.slice(0, split);
      pending = pending.slice(split + 2);
      const data = packet.split("\n").find((l) => l.startsWith("data: "));
      if (!data) continue;
      const json = JSON.parse(data.slice(6));
      if (packet.includes("event: result")) onResult(json);
      else onEvent(json);
    }
  }
}
