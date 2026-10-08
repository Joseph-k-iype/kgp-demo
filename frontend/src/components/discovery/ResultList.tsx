"use client";
import { motion, useReducedMotion } from "framer-motion";
import { Box, Database, FileText, ArrowUpRight } from "lucide-react";
import { DomainName } from "@/components/Common";
import type { DiscoveryItem } from "@/api/discovery";
export default function ResultList({
  items,
  onSelect,
}: {
  items: DiscoveryItem[];
  onSelect: (item: DiscoveryItem) => void;
}) {
  const reduced = useReducedMotion();
  return (
    <div className="discovery-result-list">
      {items.map((item, index) => {
        const Icon =
          item.kind === "product"
            ? Box
            : item.kind === "document"
              ? FileText
              : Database;
        return (
          <motion.article
            className="discovery-result"
            key={item.id}
            initial={reduced ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.2,
              delay: reduced ? 0 : Math.min(index, 5) * 0.024,
            }}
          >
            <div className="result-provenance">
              <Icon size={14} />
              <span>
                <DomainName id={item.domain_id} />
              </span>
              <span className="provenance-dot">·</span>
              <span>{item.source_type}</span>
            </div>
            <button
              className="result-title"
              aria-label={item.title}
              onClick={() => onSelect(item)}
            >
              {item.title}
              <ArrowUpRight size={16} />
            </button>
            <p>{item.excerpt.replace(/^#+\s*/, "").replace(/\n/g, " ")}</p>
            <div className="result-foot">
              <span>
                {item.kind === "product"
                  ? "Knowledge product"
                  : item.kind === "document"
                    ? "Document"
                    : "Data asset"}
              </span>
              {item.steward && <span>{item.steward}</span>}
              {item.quality != null && (
                <span className="result-quality">{item.quality}% quality</span>
              )}
            </div>
          </motion.article>
        );
      })}
    </div>
  );
}
