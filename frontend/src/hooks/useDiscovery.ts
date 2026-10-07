"use client";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { DiscoveryPage } from "@/api/discovery";
export function useDiscovery(
  {
    query,
    domainId,
    type,
    sort,
    page,
  }: {
    query: string;
    domainId: string | null;
    type: string;
    sort: string;
    page: number;
  },
  token: string,
) {
  const params = new URLSearchParams({
    q: query,
    type,
    sort,
    page: String(page),
    page_size: "20",
  });
  if (domainId) params.set("domain_id", domainId);
  const key = token + ":" + params;
  const [state, setState] = useState<{
    key: string;
    data: DiscoveryPage | null;
    error: string;
    loading: boolean;
  }>({ key: "", data: null, error: "", loading: false });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (query.trim().length < 3) {
      setState({ key, data: null, error: "", loading: false });
      return;
    }
    const controller = new AbortController();
    let alive = true;
    setState({ key, data: null, error: "", loading: true });
    api<DiscoveryPage>("/discovery/search?" + params, token, {
      signal: controller.signal,
    })
      .then((data) => {
        if (alive) setState({ key, data, error: "", loading: false });
      })
      .catch((e) => {
        if (alive && e.name !== "AbortError")
          setState({ key, data: null, error: e.message, loading: false });
      });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [key, revision]);
  return {
    ...(state.key === key
      ? state
      : { data: null, error: "", loading: query.length >= 3 }),
    retry: () => setRevision((r) => r + 1),
  };
}
