"use client";
import { useEffect, useMemo, useState } from "react";
import { useReducedMotion } from "framer-motion";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  MiniMap,
  Controls,
  MarkerType,
  Position,
  useReactFlow,
  type Node,
  type Edge,
} from "@xyflow/react";
import ELK from "elkjs/lib/elk.bundled.js";
import type { components } from "@/api/generated";
import "@xyflow/react/dist/style.css";

type Graph = Omit<components["schemas"]["GraphPage"], "nodes"> & {
  nodes: (components["schemas"]["GraphNode"] & { aliases?: string[] })[];
};
type Props = { graph: Graph; selected: string; onSelect: (id: string) => void };
const elk = new ELK();
function Explorer({ graph, selected, onSelect }: Props) {
  const flow = useReactFlow();
  const reduced = useReducedMotion();
  const [direction, setDirection] = useState("RIGHT");
  const [kind, setKind] = useState("");
  const [relation, setRelation] = useState("");
  const [query, setQuery] = useState("");
  const [list, setList] = useState(false);
  const [local, setLocal] = useState(false);
  const [governing, setGoverning] = useState(true);
  const [layout, setLayout] = useState<{ key: string; nodes: Node[] }>({
    key: "",
    nodes: [],
  });
  const [layoutError, setLayoutError] = useState("");
  const kinds = [...new Set(graph.nodes.map((node) => node.kind))].sort();
  const relations = [...new Set(graph.edges.map((edge) => edge.label))].sort();
  const visible = useMemo(() => {
    const adjacent = new Set([selected]);
    graph.edges
      .filter((edge) => edge.source === selected || edge.target === selected)
      .forEach((edge) => {
        adjacent.add(edge.source);
        adjacent.add(edge.target);
      });
    const relevant = new Set([graph.root]);
    graph.edges
      .filter((edge) => edge.source_ref)
      .forEach((edge) => {
        relevant.add(edge.source);
        relevant.add(edge.target);
      });
    return graph.nodes.filter(
      (node) =>
        (!kind || node.kind === kind) &&
        (!local || adjacent.has(node.id)) &&
        (!governing || relevant.has(node.id)),
    );
  }, [graph, kind, local, selected, governing]);
  const edges = useMemo(() => {
    const ids = new Set(visible.map((node) => node.id));
    return graph.edges
      .filter(
        (edge) =>
          ids.has(edge.source) &&
          ids.has(edge.target) &&
          (!relation || edge.label === relation) &&
          (!governing || Boolean(edge.source_ref)),
      )
      .map(
        (edge, index): Edge => ({
          id: edge.source + "-" + edge.target + "-" + edge.label + "-" + index,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          type: "smoothstep",
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edge.source_ref ? "#b94a48" : "#aaa39e",
          },
          style: {
            stroke: edge.source_ref ? "#b94a48" : "#c5bfba",
            strokeWidth:
              edge.source === selected || edge.target === selected ? 2 : 1,
            strokeDasharray: edge.source_ref ? undefined : "4 4",
          },
          labelStyle: { fill: "#706865", fontSize: 10 },
          labelBgStyle: { fill: "#faf9f7" },
        }),
      );
  }, [graph, visible, relation, selected, governing]);
  const key = JSON.stringify([
    visible.map((node) => node.id),
    edges.map((edge) => edge.id),
    direction,
  ]);
  useEffect(() => {
    let active = true;
    setLayoutError("");
    elk
      .layout({
        id: "root",
        layoutOptions: {
          "elk.algorithm": "layered",
          "elk.direction": direction,
          "elk.spacing.nodeNode": "45",
          "elk.layered.spacing.nodeNodeBetweenLayers": "115",
        },
        children: visible.map((node) => ({
          id: node.id,
          width: 200,
          height: 76,
        })),
        edges: edges.map((edge) => ({
          id: edge.id,
          sources: [edge.source],
          targets: [edge.target],
        })),
      })
      .then((result) => {
        if (!active) return;
        setLayout({
          key,
          nodes: visible.map((node) => {
            const position = result.children?.find(
              (child) => child.id === node.id,
            );
            return {
              id: node.id,
              width: 200,
              height: 76,
              position: { x: position?.x || 0, y: position?.y || 0 },
              data: {
                label: (
                  <>
                    <small>{node.kind}</small>
                    <strong>{node.name}</strong>
                  </>
                ),
              },
              sourcePosition:
                direction === "RIGHT" ? Position.Right : Position.Bottom,
              targetPosition:
                direction === "RIGHT" ? Position.Left : Position.Top,
              style: { width: 200, height: 76 },
            };
          }),
        });
      })
      .catch(() => {
        if (active) {
          setLayoutError(
            "Graph layout could not be calculated. Use the accessible list below.",
          );
          setList(true);
        }
      });
    return () => {
      active = false;
    };
  }, [key]); // key includes every layout input; stale asynchronous results are discarded.
  const nodes =
    layout.key === key
      ? layout.nodes.map((node) => ({
          ...node,
          selected: node.id === selected,
        }))
      : [];
  useEffect(() => {
    if (layout.key !== key || !layout.nodes.length) return;
    const frame = requestAnimationFrame(() => {
      void flow.fitView({ padding: 0.2, duration: reduced ? 0 : 240 });
    });
    return () => cancelAnimationFrame(frame);
  }, [layout, key, flow, reduced]);
  const matches = query.trim()
    ? visible
        .filter((node) =>
          (node.name + " " + node.id + " " + (node.aliases || []).join(" "))
            .toLowerCase()
            .includes(query.toLowerCase()),
        )
        .slice(0, 8)
    : [];
  function focus(id: string) {
    onSelect(id);
    const node = flow.getNode(id);
    if (node)
      void flow.setCenter(node.position.x + 100, node.position.y + 38, {
        zoom: 1.1,
        duration: reduced ? 0 : 240,
      });
  }
  return (
    <div className="ontology-flow">
      <div className="ontology-tools">
        <input
          aria-label="Find graph node"
          placeholder="Find a node…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select
          aria-label="Graph node type"
          value={kind}
          onChange={(event) => setKind(event.target.value)}
        >
          <option value="">All node types</option>
          {kinds.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          aria-label="Graph relationship type"
          value={relation}
          onChange={(event) => setRelation(event.target.value)}
        >
          <option value="">All relationships</option>
          {relations.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          aria-label="Graph layout direction"
          value={direction}
          onChange={(event) => setDirection(event.target.value)}
        >
          <option value="RIGHT">Left to right</option>
          <option value="DOWN">Top to bottom</option>
        </select>
        <button
          onClick={() =>
            void flow.fitView({ padding: 0.2, duration: reduced ? 0 : 240 })
          }
        >
          Fit graph
        </button>
        <button
          aria-pressed={governing}
          onClick={() => setGoverning(!governing)}
        >
          Governing paths
        </button>
        <button aria-pressed={local} onClick={() => setLocal(!local)}>
          Selected neighborhood
        </button>
        <button aria-pressed={list} onClick={() => setList(!list)}>
          Accessible list
        </button>
      </div>
      {matches.length > 0 && (
        <div className="ontology-matches">
          {matches.map((node) => (
            <button key={node.id} onClick={() => focus(node.id)}>
              Focus {node.name}
              {node.aliases?.length ? " · " + node.aliases.join(", ") : ""}
            </button>
          ))}
        </div>
      )}
      {layoutError && <p role="alert">{layoutError}</p>}
      {list ? (
        <div className="ontology-accessible">
          <ul>
            {visible.map((node) => (
              <li key={node.id}>
                <button
                  onClick={() => onSelect(node.id)}
                  aria-pressed={node.id === selected}
                >
                  {node.name} · {node.kind}
                </button>
              </li>
            ))}
          </ul>
          <h3>Relationships</h3>
          <ul>
            {edges.map((edge) => (
              <li key={edge.id}>
                {graph.nodes.find((node) => node.id === edge.source)?.name} →{" "}
                {edge.label} →{" "}
                {graph.nodes.find((node) => node.id === edge.target)?.name}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="ontology-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodeClick={(_, node) => onSelect(node.id)}
            nodesDraggable={false}
            nodesConnectable={false}
            edgesFocusable={true}
            colorMode="light"
            minZoom={0.15}
            maxZoom={2}
            onlyRenderVisibleElements
            fitView
          >
            <Background gap={24} size={1} color="#ded8d3" />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              zoomable
              nodeColor={(node) => (node.selected ? "#c63030" : "#e7d8d2")}
            />
          </ReactFlow>
        </div>
      )}
      <div className="ontology-legend">
        Solid edges: source-backed assertions · Dashed edges: catalog or
        vocabulary relationships · {visible.length} nodes / {edges.length}{" "}
        relationships
        {graph.truncated
          ? " · Bounded view; expand a node to explore further"
          : ""}
      </div>
    </div>
  );
}
export default function OntologyGraph(props: Props) {
  return (
    <ReactFlowProvider>
      <Explorer {...props} />
    </ReactFlowProvider>
  );
}
