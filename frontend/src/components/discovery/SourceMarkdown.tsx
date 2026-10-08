"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Render source text as data: no HTML, images, embeds or executable MDX. */
export default function SourceMarkdown({ text }: { text: string }) {
  return (
    <div className="source-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          img: () => null,
          a: ({ children }) => <span>{children}</span>,
          table: ({ children }) => (
            <div className="markdown-table">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
