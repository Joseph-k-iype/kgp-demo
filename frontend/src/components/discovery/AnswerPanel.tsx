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
import SourceMarkdown from "./SourceMarkdown";
import { DomainName } from "@/components/Common";
type Props = {
  run: Run | null;
  busy: boolean;
  error: string;
  domainId: string | null;
  onGenerate: (mode?: "llm" | "extractive") => void;
  onCancel: () => void;
  onReconnect: () => void;
  onEvidence: (id: string, quote?: string) => void;
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
  const displayed = new Set<number>();
  const sections = (run?.answer_sections || [])
    .map((section) => ({
      title: section.title,
      indices: section.statement_indices.filter((index) => {
        if (
          !Number.isInteger(index) ||
          index < 0 ||
          index >= (run?.statements.length || 0) ||
          displayed.has(index)
        )
          return false;
        displayed.add(index);
        return true;
      }),
    }))
    .filter((section) => section.indices.length > 0);
  const remaining = (run?.statements || [])
    .map((_, index) => index)
    .filter((index) => !displayed.has(index));
  if (remaining.length)
    sections.push({
      title: sections.length ? "Additional findings" : "Answer",
      indices: remaining,
    });
  function citationLabel(index: number, id: string) {
    const statement = run!.statements[index];
    const support = statement.supporting_locators?.find(
      (item) => item.evidence_id === id,
    );
    const evidence = run!.evidence.find((item) => item.id === id);
    const title =
      typeof support?.source_title === "string"
        ? support.source_title
        : evidence?.source_title || evidence?.name || "Supporting source";
    const ref = support?.source_ref;
    const locator =
      ref &&
      typeof ref === "object" &&
      "locator" in ref &&
      typeof ref.locator === "string"
        ? ref.locator
        : evidence?.source_ref?.locator || evidence?.provenance?.row_id;
    return title + (locator ? " · " + locator : "");
  }

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
            sections.map((section, sectionIndex) => (
              <section
                className="answer-section"
                key={sectionIndex}
                aria-label={section.title}
              >
                <h3>{section.title}</h3>
                {section.indices.map((i) => {
                  const statement = run.statements[i];
                  return (
                    <div key={i} className="answer-statement">
                      <SourceMarkdown text={statement.text} />
                      <span className="answer-citations">
                        {statement.evidence_ids
                          .filter((id) =>
                            run.evidence.some((item) => item.id === id),
                          )
                          .map((id) => {
                            const label = citationLabel(i, id);
                            return (
                              <button
                                key={id}
                                aria-label={"Open source: " + label}
                                onClick={() => {
                                  const citation =
                                    statement.supporting_locators?.find(
                                      (item) => item.evidence_id === id,
                                    );
                                  onEvidence(
                                    id,
                                    typeof citation?.quote === "string"
                                      ? citation.quote
                                      : undefined,
                                  );
                                }}
                              >
                                <ArrowUpRight size={11} />
                                {label}
                              </button>
                            );
                          })}
                      </span>
                    </div>
                  );
                })}
              </section>
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
                    sections
                      .map(
                        (section) =>
                          "## " +
                          section.title +
                          "\n\n" +
                          section.indices
                            .map(
                              (index) =>
                                run.statements[index].text +
                                "\n\n" +
                                run.statements[index].evidence_ids
                                  .map((id) => citationLabel(index, id))
                                  .join("; "),
                            )
                            .join("\n\n"),
                      )
                      .join("\n\n"),
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
