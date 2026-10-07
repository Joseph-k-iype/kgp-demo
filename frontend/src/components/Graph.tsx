"use client";
import type { GraphData } from "@/api/client";
export default function Graph({
  data,
  selected,
  onSelect,
}: {
  data: GraphData;
  selected?: string;
  onSelect: (id: string) => void;
}) {
  const root = data.nodes.find((n) => n.id === data.root) || data.nodes[0];
  const others = data.nodes.filter((n) => n !== root);
  const positions: Record<string, { x: number; y: number }> = {};
  if (root) positions[root.id] = { x: 400, y: 265 };
  others.forEach((n, i) => {
    const side = i % 2 === 0 ? -1 : 1;
    const row = Math.floor(i / 2);
    positions[n.id] = {
      x: 400 + side * (220 + (row % 2) * 30),
      y: 65 + row * (others.length > 10 ? 67 : 100),
    };
  });
  return (
    <div className="graph-canvas">
      <svg viewBox="0 0 800 550" role="img" aria-label="RDF relationship graph">
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#afc3db" />
          </marker>
        </defs>
        {data.edges.map((e, i) => {
          const a = positions[e.source],
            b = positions[e.target];
          if (!a || !b) return null;
          return (
            <g key={i}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="#b7cbe1"
                strokeWidth="1.2"
                markerEnd="url(#arrow)"
              />
              <text
                x={(a.x + b.x) / 2}
                y={(a.y + b.y) / 2 - 5}
                fontSize="8"
                fill="#83a0bd"
                textAnchor="middle"
              >
                {e.label}
              </text>
            </g>
          );
        })}
        {data.nodes.map((n) => {
          const p = positions[n.id];
          const main = n === root,
            active = selected === n.id;
          return (
            <g
              className={"graph-node" + (main ? " root-node" : "")}
              key={n.id}
              transform={`translate(${p.x},${p.y})`}
              role="button"
              tabIndex={0}
              aria-label={"Inspect " + n.name}
              onClick={() => onSelect(n.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(n.id);
                }
              }}
            >
              <rect
                x={main ? -78 : -90}
                y={-24}
                width={main ? 156 : 180}
                height={48}
                rx="7"
                fill={
                  main ? "#e44436" : n.kind === "Concept" ? "#e9e6df" : "#fff"
                }
                stroke={
                  active
                    ? "#e44436"
                    : main
                      ? "#e44436"
                      : n.kind === "Concept"
                        ? "#c4c0b6"
                        : "#d2e0ef"
                }
                strokeWidth={active ? 2 : 1}
              />
              <text
                y={-3}
                textAnchor="middle"
                fill={main ? "white" : "#36322d"}
                fontWeight="500"
              >
                {n.name.length > 26 ? n.name.slice(0, 25) + "…" : n.name}
              </text>
              <text
                y={12}
                textAnchor="middle"
                fill={main ? "#ffe2da" : "#8a8379"}
                style={{ fontSize: 8 }}
              >
                {main ? "Ontology concept" : n.kind}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="graph-legend">
        <span>
          <i className="dot" style={{ background: "#e44436" }} /> Selected
          concept
        </span>
        <span>
          <i className="dot" style={{ background: "#7fc9b9" }} /> Concept
        </span>
        <span>
          <i className="dot" style={{ background: "#9eb6d0" }} /> Governed asset
        </span>
      </div>
    </div>
  );
}
