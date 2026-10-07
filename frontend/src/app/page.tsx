"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Search, History, X } from "lucide-react";
import { useSession } from "@/components/Shell";
import SearchBox, { SearchSubmission } from "@/components/discovery/SearchBox";
import { prepareSearch } from "@/api/discovery";
const examples = [
  "Find counterparty exposure and due diligence evidence",
  "Which policies govern treasury liquidity?",
  "Show technology service health sources",
];
export default function SearchHome() {
  const { persona } = useSession();
  const router = useRouter();
  const [recent, setRecent] = useState<string[]>([]);
  useEffect(() => {
    try {
      const items = JSON.parse(
        localStorage.getItem("kpm-recent-" + persona) || "[]",
      );
      setRecent(
        Array.isArray(items)
          ? items.filter((q) => typeof q === "string").slice(0, 5)
          : [],
      );
    } catch {
      setRecent([]);
    }
  }, [persona]);
  function submit(value: SearchSubmission) {
    router.push(prepareSearch(value, persona));
  }
  return (
    <section className="knowledge-home">
      <div className="home-introduction">
        <h1>
          Find knowledge.
          <br />
          <span>Understand it.</span>
        </h1>
        <p>Your enterprise knowledge, one question away.</p>
      </div>
      <SearchBox onSubmit={submit} />
      <div className="example-queries" aria-label="Example questions">
        {examples.map((q) => (
          <button key={q} onClick={() => submit({ query: q, domainId: null })}>
            <Search size={17} />
            <span>{q}</span>
            <ArrowRight size={15} />
          </button>
        ))}
      </div>
      <Link className="browse-domains" href="/domains">
        Browse all domains <ArrowRight size={17} />
      </Link>
      {recent.length > 0 && (
        <div className="recent-searches">
          <div>
            <span>
              <History size={14} />
              Recent searches
            </span>
            <button
              aria-label="Clear recent searches"
              onClick={() => {
                localStorage.removeItem("kpm-recent-" + persona);
                setRecent([]);
              }}
            >
              <X size={13} />
              Clear
            </button>
          </div>
          {recent.map((q) => (
            <button
              key={q}
              onClick={() => submit({ query: q, domainId: null })}
            >
              {q}
              <ArrowRight size={13} />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
