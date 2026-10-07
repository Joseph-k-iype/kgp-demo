"use client";
import { useEffect, useRef, useState } from "react";
import { api, Run, streamRun } from "@/api/client";
import { prepareSearch, searchKey } from "@/api/discovery";
import {
  activateContext,
  claimIntent,
  intentFor,
  savedRun,
  observeRun,
  cancelEntry,
} from "@/api/knowledgeRuns";
export function useKnowledgeRun(
  {
    query,
    domainId,
    persona,
  }: { query: string; domainId: string | null; persona: string },
  token: string,
) {
  const key = searchKey(query, domainId, persona);
  const [state, setState] = useState<{
    key: string;
    run: Run | null;
    busy: boolean;
    error: string;
  }>({ key: "", run: null, busy: false, error: "" });
  const [revision, setRevision] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const generationRef = useRef(0);
  useEffect(() => {
    let alive = true;
    activateContext(key);
    async function load() {
      const generation = ++generationRef.current;
      controller.current?.abort();
      const valid = () => alive && generation === generationRef.current;
      setState({ key, run: null, busy: false, error: "" });
      if (query.length < 3) return;
      const intent = intentFor(query, domainId, persona),
        saved = savedRun(key);
      try {
        let run: Run;
        if (intent && (!intent.claimed || saved?.intentId !== intent.id)) {
          setState({ key, run: null, busy: true, error: "" });
          run = await claimIntent(intent, token);
        } else if (saved) {
          run = await api<Run>("/search/runs/" + saved.id, token);
        } else if (intent) {
          setState({ key, run: null, busy: true, error: "" });
          run = await claimIntent(intent, token);
        } else return;
        if (!valid()) return;
        observeRun(key, run);
        const pending = ["pending", "running"].includes(run.status);
        setState({ key, run, busy: pending, error: "" });
        if (!pending) return;
        const c = new AbortController();
        controller.current = c;
        let finished = false;
        await streamRun(
          run.run_id,
          token,
          (event) => {
            if (valid())
              setState((s) =>
                s.key === key && s.run
                  ? {
                      ...s,
                      run: {
                        ...s.run,
                        events: [
                          ...s.run.events.filter(
                            (e) => e.sequence !== event.sequence,
                          ),
                          event,
                        ].sort((a, b) => a.sequence - b.sequence),
                      },
                    }
                  : s,
              );
          },
          (result) => {
            finished = true;
            observeRun(key, result);
            if (valid()) setState({ key, run: result, busy: false, error: "" });
          },
          c.signal,
        );
        if (!finished && valid())
          setState((s) => ({
            ...s,
            error:
              "The progress connection paused. Reconnect to continue following this answer.",
          }));
      } catch (e) {
        if (valid() && (e as Error).name !== "AbortError")
          setState((s) => ({
            ...s,
            key,
            busy: false,
            error: (e as Error).message,
          }));
      }
    }
    void load();
    function submitted() {
      if (intentFor(query, domainId, persona)) void load();
    }
    window.addEventListener("kpm-search-submitted", submitted);
    return () => {
      alive = false;
      generationRef.current++;
      controller.current?.abort();
      window.removeEventListener("kpm-search-submitted", submitted);
    };
  }, [key, token, revision]);
  async function cancel() {
    const generation = generationRef.current;
    try {
      const entry = await cancelEntry(key);
      const current = state.key === key ? state.run : null;
      const result =
        entry ||
        (current
          ? await api<Run>(
              "/search/runs/" + current.run_id + "/cancel",
              token,
              { method: "POST" },
            )
          : null);
      if (result && generation === generationRef.current) {
        controller.current?.abort();
        observeRun(key, result);
        setState({ key, run: result, busy: false, error: "" });
      }
    } catch (e) {
      if (generation === generationRef.current)
        setState((s) => ({ ...s, error: (e as Error).message }));
    }
  }
  return {
    ...(state.key === key ? state : { run: null, busy: false, error: "" }),
    cancel,
    reconnect: () => setRevision((r) => r + 1),
    submit: (mode: "llm" | "extractive" = "llm") =>
      prepareSearch({ query, domainId }, persona, mode, true),
  };
}
