
import { useEffect, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { getDependencyGraph } from "./api";

function GraphCanvas() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    getDependencyGraph()
      .then((data) => {
        if (!active) return;

        const nodes = (data.nodes || []).map((node, index) => ({
          id: node.id,
          position: {
            x: 100 + (index % 3) * 250,
            y: 80 + Math.floor(index / 3) * 150,
          },
          data: { label: node.label || node.id },
          style: {
            background: "#151f35",
            color: "#e2e8f0",
            border: "1px solid #6366f1",
            borderRadius: 12,
            padding: 14,
            width: 180,
            fontSize: 12,
          },
        }));

        const edges = (data.edges || []).map((edge, index) => ({
          id: `edge-${index}`,
          source: edge.source,
          target: edge.target,
          label: edge.label || "imports",
          animated: true,
          style: { stroke: "#818cf8", strokeWidth: 2 },
          labelStyle: { fill: "#c7d2fe", fontSize: 11 },
        }));

        setGraph({ nodes, edges });
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.message || "Unable to load dependency graph.");
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-slate-400">
        Loading dependency graph…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        {error}
      </div>
    );
  }

  if (!graph.nodes.length) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No files found. Upload and analyze a Python project first.
      </div>
    );
  }

  return (
    <div className="h-[480px] overflow-hidden rounded-xl border border-slate-800 bg-[#090f1c]">
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.3}
        maxZoom={2}
      >
        <Background color="#26334a" gap={24} />
        <Controls />
        <MiniMap
          nodeColor="#6366f1"
          maskColor="rgba(8, 13, 24, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}

export default function DependencyGraph() {
  return (
    <ReactFlowProvider>
      <GraphCanvas />
    </ReactFlowProvider>
  );
}
