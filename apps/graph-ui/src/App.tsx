import React from "react";
import { Layout } from "./components/Layout";
import { DocumentGraph } from "./components/DocumentGraph";
import { useGraphStore } from "./store/useGraphStore";
import { CLUSTER_COLOR_MAP } from "./hooks/useClusterColor";
import { ShieldCheck, Network, Layers, Sparkles, Orbit } from "lucide-react";

export const App: React.FC = () => {
  const {
    nodes,
    links,
    selectedNode,
    setSelectedNode,
    dimension,
    setDimension,
    activeCluster,
    setActiveCluster,
  } = useGraphStore();

  const activeNode = selectedNode || nodes[0];

  return (
    <Layout
      headerBar={
        <div className="glass-panel rounded-2xl px-5 py-3.5 flex items-center justify-between">
          {/* Logo & Product Title */}
          <div className="flex items-center space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400/20 to-blue-600/30 border border-cyan-400/40 flex items-center justify-center text-cyan-400 shadow-sm shadow-cyan-400/20">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-base tracking-wider text-white">
                  VERITAS
                </span>
                <span className="text-[10px] font-mono tracking-widest bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 px-2 py-0.5 rounded uppercase">
                  Phase 1 & 2: Solar System WebGL
                </span>
              </div>
              <p className="text-[11px] text-slate-400 tracking-tight">
                Research Intelligence. Grounded in Truth.
              </p>
            </div>
          </div>

          {/* Cluster Filter Pills */}
          <div className="hidden lg:flex items-center space-x-2">
            <button
              onClick={() => setActiveCluster(null)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                activeCluster === null
                  ? "bg-white/15 text-white border border-white/30"
                  : "text-slate-400 hover:text-white border border-transparent"
              }`}
            >
              All Clusters ({nodes.length})
            </button>
            {Object.entries(CLUSTER_COLOR_MAP).map(([clusterId, meta]) => (
              <button
                key={clusterId}
                onClick={() => setActiveCluster(clusterId === activeCluster ? null : clusterId)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center space-x-1.5 transition-all border ${
                  activeCluster === clusterId
                    ? "bg-white/15 text-white border-white/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 border-white/5"
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: meta.hex }}
                />
                <span className="truncate max-w-[120px]">{meta.name}</span>
              </button>
            ))}
          </div>

          {/* Controls: Mode & Status */}
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-1.5 text-xs font-mono text-cyan-400 bg-cyan-950/40 px-2.5 py-1 rounded-lg border border-cyan-800/40">
              <Orbit className="w-3.5 h-3.5 animate-spin" style={{ animationDuration: "12s" }} />
              <span>D3 Orbit Tuned</span>
            </div>

            <div className="flex items-center space-x-1 bg-black/40 p-1 rounded-xl border border-white/10">
              <button
                onClick={() => setDimension("2d")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                  dimension === "2d"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                2D
              </button>
              <button
                onClick={() => setDimension("3d")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                  dimension === "3d"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                3D WebGL
              </button>
            </div>
          </div>
        </div>
      }
      overlayPanel={
        <div className="glass-panel rounded-2xl p-6 flex flex-col h-full border border-white/10 backdrop-blur-xl">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Document Tree Inspector
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">
              Level {activeNode.level} {activeNode.level === 0 ? "• Sun" : activeNode.level === 1 ? "• Planet" : activeNode.level === 2 ? "• Moon" : "• Satellite"}
            </span>
          </div>

          {/* Node Metadata & Context Panel */}
          <div className="mt-4 space-y-4 flex-1 overflow-y-auto pr-1">
            <div>
              <div className="flex items-center space-x-2 mb-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{
                    backgroundColor:
                      CLUSTER_COLOR_MAP[activeNode.topic_cluster]?.hex || "#00f5ff",
                  }}
                />
                <span className="text-xs text-slate-400 font-medium">
                  {CLUSTER_COLOR_MAP[activeNode.topic_cluster]?.name || activeNode.topic_cluster}
                </span>
              </div>
              <h2 className="text-base font-bold text-white leading-snug">
                {activeNode.label}
              </h2>
            </div>

            <div className="bg-black/40 rounded-xl p-4 border border-white/5 space-y-2">
              <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider block">
                Panel Payload (Context Content)
              </span>
              <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                {activeNode.panel_payload}
              </p>
            </div>

            {/* Quick Navigation / Orbital Roster */}
            <div className="pt-2">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-2">
                Hierarchy Nodes ({nodes.length} Total)
              </span>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {nodes.map((node) => (
                  <button
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all flex items-center justify-between border ${
                      node.id === activeNode.id
                        ? "bg-cyan-500/15 border-cyan-400/40 text-cyan-200"
                        : "bg-white/[0.02] border-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
                    }`}
                  >
                    <span className="truncate pr-2">{node.label}</span>
                    <span className="text-[9px] font-mono opacity-60">L{node.level}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Footer Stats */}
          <div className="pt-4 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex items-center space-x-1.5">
              <Network className="w-3.5 h-3.5 text-cyan-400" />
              <span>{links.length} Active Orbit Links</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Three.js Engine</span>
            </div>
          </div>
        </div>
      }
    >
      {/* Mounted Full-Bleed 3D WebGL Force Graph Canvas */}
      <DocumentGraph />
    </Layout>
  );
};

export default App;
