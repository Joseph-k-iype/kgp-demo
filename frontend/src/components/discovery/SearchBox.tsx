"use client";
import { useEffect, useRef, useState } from "react";
import { Search, Globe2 } from "lucide-react";
import { useData, RecordItem } from "@/api/client";
import { useSession } from "@/components/Shell";
export type SearchSubmission = { query: string; domainId: string | null };
export type SearchBoxProps = {
  query?: string;
  domainId?: string | null;
  onSubmit: (value: SearchSubmission) => void;
  compact?: boolean;
};
export default function SearchBox({
  query = "",
  domainId = null,
  onSubmit,
  compact = false,
}: SearchBoxProps) {
  const { token } = useSession();
  const domains = useData<RecordItem[]>("/domains", token);
  const [draft, setDraft] = useState(query),
    [domain, setDomain] = useState(domainId || "");
  const composing = useRef(false);
  useEffect(() => {
    setDraft(query);
    setDomain(domainId || "");
  }, [query, domainId]);
  return (
    <form
      role="search"
      className={"knowledge-search " + (compact ? "compact" : "")}
      onSubmit={(e) => {
        e.preventDefault();
        if (!composing.current && draft.trim().length >= 3)
          onSubmit({ query: draft.trim(), domainId: domain || null });
      }}
    >
      <Search className="search-leading" size={22} />
      <input
        type="search"
        aria-label="Search enterprise knowledge"
        placeholder="Ask a question, find data, or explore a topic…"
        minLength={3}
        maxLength={2000}
        required
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onCompositionStart={() => {
          composing.current = true;
        }}
        onCompositionEnd={() => {
          composing.current = false;
        }}
        onKeyDown={(e) => {
          if (
            e.key === "Enter" &&
            (composing.current || e.nativeEvent.isComposing)
          )
            e.preventDefault();
        }}
      />
      <div className="search-domain">
        <Globe2 size={16} />
        <select
          aria-label="Search domain"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
        >
          <option value="">All domains</option>
          {domains.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        className="knowledge-submit"
        aria-label="Search knowledge"
      >
        <Search size={22} />
      </button>
    </form>
  );
}
