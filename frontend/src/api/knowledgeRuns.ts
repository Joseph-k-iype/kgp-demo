import { api, Run } from "./client";
import { searchKey } from "./discovery";
export type SearchIntent = {
  id: string;
  key: string;
  query: string;
  domainId: string | null;
  persona: string;
  mode: "llm" | "extractive";
  submittedAt: number;
  claimed?: boolean;
};
type Entry = {
  intent: SearchIntent;
  token: string;
  promise: Promise<Run>;
  run?: Run;
  cancelled: boolean;
  cancelPromise?: Promise<Run>;
};
const entries = new Map<string, Entry>();
let active: Entry | undefined;
let activeKey = "";
const running = (run: Run) => ["pending", "running"].includes(run.status);
export function readIntent(): SearchIntent | null {
  try {
    const value = JSON.parse(
      sessionStorage.getItem("kpm-search-intent") || "null",
    );
    return value &&
      typeof value.id === "string" &&
      typeof value.query === "string" &&
      typeof value.persona === "string"
      ? value
      : null;
  } catch {
    return null;
  }
}
export function savedRun(key: string): { id: string; intentId: string } | null {
  try {
    return JSON.parse(sessionStorage.getItem("kpm-run:" + key) || "null");
  } catch {
    return null;
  }
}
function remember(entry: Entry) {
  if (entry.run && entries.get(entry.intent.key) === entry)
    sessionStorage.setItem(
      "kpm-run:" + entry.intent.key,
      JSON.stringify({ id: entry.run.run_id, intentId: entry.intent.id }),
    );
}
export function observeRun(key: string, run: Run) {
  const entry = entries.get(key);
  if (entry && entry.run?.run_id === run.run_id) {
    entry.run = run;
    remember(entry);
  }
}
export function cancelEntry(key: string): Promise<Run | null> {
  const entry = entries.get(key);
  if (!entry) return Promise.resolve(null);
  entry.cancelled = true;
  if (entry.run) {
    if (!running(entry.run)) return Promise.resolve(entry.run);
    entry.cancelPromise ??= api<Run>(
      "/search/runs/" + entry.run.run_id + "/cancel",
      entry.token,
      { method: "POST" },
    ).then((run) => {
      entry.run = run;
      remember(entry);
      return run;
    });
    return entry.cancelPromise;
  }
  return entry.promise.then((run) => (running(run) ? cancelEntry(key) : run));
}
export function activateContext(key: string) {
  activeKey = key;
  if (active && active.intent.key !== key)
    void cancelEntry(active.intent.key).catch(() => {});
  active = entries.get(key);
}
export function restoreRun(
  intent: SearchIntent,
  id: string,
  token: string,
): Promise<Run> {
  const previous = entries.get(intent.key);
  if (previous?.run?.run_id === id) return Promise.resolve(previous.run);
  if (previous?.intent.id === intent.id) return previous.promise;
  const entry: Entry = {
    intent,
    token,
    cancelled: false,
    promise: Promise.resolve(null as unknown as Run),
  };
  entries.set(intent.key, entry);
  if (activeKey === intent.key) active = entry;
  entry.promise = api<Run>("/search/runs/" + id, token).then(async (run) => {
    entry.run = run;
    if (entry.cancelled && running(run)) {
      entry.cancelPromise ??= api<Run>(
        "/search/runs/" + id + "/cancel",
        token,
        { method: "POST" },
      );
      entry.run = await entry.cancelPromise;
    }
    remember(entry);
    return entry.run;
  });
  return entry.promise;
}
export function claimIntent(intent: SearchIntent, token: string): Promise<Run> {
  const previous = entries.get(intent.key);
  if (previous?.intent.id === intent.id) return previous.promise;
  const saved = savedRun(intent.key);
  if (intent.claimed) {
    if (saved?.intentId === intent.id)
      return restoreRun(intent, saved.id, token);
    return Promise.reject(
      new Error(
        "The previous request was interrupted before its run ID was saved. Generate an answer to start a new request.",
      ),
    );
  }
  if (previous) void cancelEntry(intent.key).catch(() => {});
  if (active && active.intent.key !== intent.key)
    void cancelEntry(active.intent.key).catch(() => {});
  const current = readIntent();
  if (current?.id === intent.id)
    sessionStorage.setItem(
      "kpm-search-intent",
      JSON.stringify({ ...intent, claimed: true }),
    );
  const entry: Entry = {
    intent,
    token,
    cancelled: false,
    promise: Promise.resolve(null as unknown as Run),
  };
  entries.set(intent.key, entry);
  active = entry;
  entry.promise = api<Run>("/search/runs", token, {
    method: "POST",
    body: JSON.stringify({
      intent_id: intent.id,
      query: intent.query,
      domain_id: intent.domainId,
      mode: intent.mode || "llm",
    }),
  }).then(async (run) => {
    entry.run = run;
    remember(entry);
    if (entry.cancelled && running(run)) {
      // Cancel this specific entry, even if a newer same-query entry replaced it.
      entry.cancelPromise ??= api<Run>(
        "/search/runs/" + run.run_id + "/cancel",
        entry.token,
        { method: "POST" },
      );
      entry.run = await entry.cancelPromise;
      remember(entry);
    }
    return entry.run;
  });
  return entry.promise;
}
export function intentFor(
  query: string,
  domainId: string | null,
  persona: string,
) {
  const intent = readIntent();
  return intent?.key === searchKey(query, domainId, persona) ? intent : null;
}
