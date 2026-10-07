"use client";
import { useState } from "react";
import {
  Sparkles,
  Square,
  ArrowUpRight,
  Copy,
  Check,
  ChevronDown,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import { Run } from "@/api/client";
import { DomainName } from "@/components/Common";
type Props = {
  run: Run | null;
  busy: boolean;
  error: string;
  domainId: string | null;
  onGenerate: (mode?: "llm" | "extractive") => void;
  onCancel: () => void;
  onReconnect: () => void;
  onEvidence: (id: string) => void;
};
export default function AnswerPanel({
  run,
  busy,
  error,
  domainId,
  onGenerate,
  onCancel,
  onReconnect,
  onEvidence,
}: Props) {
  const [copied, setCopied] = useState(false);
  const complete = run?.status === "completed",
    cancelled = run?.status === "cancelled",
    failed =
      run &&
      !["pending", "running", "completed", "cancelled"].includes(run.status);
  const failure = error || run?.error || "";
  return (
    <section className="knowledge-answer" aria-label="Knowledge answer">
      <div className="answer-heading">
        <h2>
          <Sparkles size={18} />
          {run?.mode === "extractive" ? "Source excerpts" : "AI answer"}
        </h2>
        <span>
          <ShieldCheck size={12} />
          {domainId ? <DomainName id={domainId} /> : "Within your access"}
        </span>
      </div>
      {busy && (
        <div className="answer-progress" role="status">
          <span className="loader" />
          <div>
            <strong>Finding a cited answer…</strong>
            <p>
              Your results are ready to explore while we connect the evidence.
            </p>
          </div>
          <button onClick={onCancel} aria-label="Stop answer">
            <Square size={12} />
            Stop
          </button>
        </div>
      )}
      {!busy && cancelled && (
        <div className="answer-empty">
          <strong>Answer cancelled</strong>
          <p>Your search results are still available below.</p>
          <button onClick={() => onGenerate()} className="answer-action">
            Generate answer <RotateCcw size={13} />
          </button>
        </div>
      )}
      {failure && (
        <div className="answer-error" role="alert">
          <p>{failure}</p>
          {error && run && ["pending", "running"].includes(run.status) ? (
            <button onClick={onReconnect}>Reconnect</button>
          ) : (
            <button disabled={busy} onClick={() => onGenerate()}>
              Retry answer
            </button>
          )}
        </div>
      )}
      {!busy && !run && !error && (
        <div className="answer-empty">
          <p>
            Generate a cited answer to connect the knowledge behind these
            results.
          </p>
          <button className="answer-action" onClick={() => onGenerate()}>
            Generate answer <Sparkles size={14} />
          </button>
        </div>
      )}
      {complete && (
        <div className="answer-content">
          {run.statements.length === 0 ? (
            <p>No supported answer was found within this search scope.</p>
          ) : (
            run.statements.map((statement, i) => (
              <div key={i} className="answer-statement">
                <p>{statement.text}</p>
                <span className="answer-citations">
                  {statement.evidence_ids.map((id) => {
                    const n = run.evidence.findIndex((e) => e.id === id) + 1;
                    return (
                      <button
                        key={id}
                        aria-label={"Open evidence " + n}
                        onClick={() => onEvidence(id)}
                      >
                        <ArrowUpRight size={11} />
                        Source {n}
                      </button>
                    );
                  })}
                </span>
              </div>
            ))
          )}
          {(run.gaps.length > 0 || run.uncertainty) && (
            <div className="answer-coverage">
              {run.gaps.map((gap, i) => (
                <p key={i}>{gap}</p>
              ))}
              {run.uncertainty && <p>{run.uncertainty}</p>}
            </div>
          )}
          <div className="answer-bottom">
            <span>
              {run.mode === "extractive"
                ? "Retrieved source excerpts"
                : "Answer grounded in synthetic source evidence"}
            </span>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    run.statements.map((s) => s.text).join("\n\n"),
                  );
                  setCopied(true);
                } catch {
                  setCopied(false);
                }
              }}
            >
              {copied ? <Check size={13} /> : <Copy size={13} />}{" "}
              {copied ? "Copied" : "Copy answer"}
            </button>
          </div>
        </div>
      )}
      {(run || failed) && (
        <details className="answer-steps">
          <summary>
            Search steps <ChevronDown size={13} />
          </summary>
          <ol>
            {run?.events.map((event) => (
              <li key={event.sequence}>
                <span
                  className={
                    "step-dot " + (event.status === "completed" ? "done" : "")
                  }
                />
                {event.summary}
              </li>
            ))}
          </ol>
        </details>
      )}
      <details className="answer-options">
        <summary>Answer options</summary>
        <button disabled={busy} onClick={() => onGenerate("extractive")}>
          Use source excerpts
        </button>
        <p>Retrieve the underlying evidence without LLM synthesis.</p>
      </details>
    </section>
  );
}
