import React, { useState } from "react";
import { Layout } from "./components/Layout";
import { DocumentGraph } from "./components/DocumentGraph";
import { useGraphStore } from "./store/useGraphStore";
import { CLUSTER_COLOR_MAP } from "./hooks/useClusterColor";
import { findHierarchyPath } from "./utils/pathfinding";
import {
  ShieldCheck,
  Network,
  Layers,
  Sparkles,
  Search,
  X,
  Zap,
  CheckCircle2,
  ChevronRight,
  Compass,
} from "lucide-react";

const SAMPLE_SEARCH_PRESETS = [
  { label: "RRF Formula", query: "RRF" },
  { label: "Strict Abstention", query: "abstention" },
  { label: "SHA-256 Dedup", query: "hash" },
  { label: "ReAct Cycle", query: "react" },
  { label: "GDPR Purge", query: "gdpr" },
];

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
    searchQuery,
    isSearching,
    searchPath,
    setSearchState,
    clearSearch,
  } = useGraphStore();

  const [inputVal, setInputVal] = useState("");

  const activeNode = selectedNode || nodes[0];

  // Execute BFS pathfinding & initiate Tracer Pulse
  const executeSearch = (rawQuery: string) => {
    const q = rawQuery.trim().toLowerCase();
    if (!q) {
      clearSearch();
      setInputVal("");
      return;
    }

    setInputVal(rawQuery);

    // Prefer Level 3 Flashcard matches
    let matchedNode = nodes.find(
      (n) =>
        n.level === 3 &&
        (n.label.toLowerCase().includes(q) || n.panel_payload.toLowerCase().includes(q))
    );

    // Fallback to any node matching query
    if (!matchedNode) {
      matchedNode = nodes.find(
        (n) =>
          n.label.toLowerCase().includes(q) ||
          n.panel_payload.toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q)
      );
    }

    if (matchedNode) {
      const { nodeIds, links: pathLinks } = findHierarchyPath(
        nodes,
        links,
        "node_root",
        matchedNode.id
      );

      setSearchState({
        query: rawQuery,
        isSearching: true,
        searchPath: nodeIds,
        targetNode: matchedNode,
        searchLinks: pathLinks,
      });
    } else {
      setSearchState({
        query: rawQuery,
        isSearching: false,
        searchPath: [],
        targetNode: null,
        searchLinks: [],
      });
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(inputVal);
  };

  const handleClear = () => {
    setInputVal("");
    clearSearch();
  };

  return (
    <Layout
      headerBar={
        <div className="glass-panel rounded-2xl px-5 py-3 flex flex-col md:flex-row items-center justify-between gap-3 shadow-2xl">
          {/* Logo & Product Identity */}
          <div className="flex items-center space-x-3 w-full md:w-auto">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400/20 to-blue-600/30 border border-cyan-400/40 flex items-center justify-center text-cyan-400 shadow-sm shadow-cyan-400/20 shrink-0">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-base tracking-wider text-white">
                  VERITAS
                </span>
                <span className="text-[10px] font-mono tracking-widest bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 px-2 py-0.5 rounded uppercase">
                  Phase 5: Tracer Pulse
                </span>
              </div>
              <p className="text-[11px] text-slate-400 tracking-tight">
                Research Intelligence. Grounded in Truth.
              </p>
            </div>
          </div>

          {/* Frosted Glass Search Bar with Preset Pills */}
          <div className="flex-1 max-w-xl w-full flex flex-col space-y-1.5">
            <form onSubmit={handleFormSubmit} className="relative w-full">
              <Search className="w-4 h-4 text-cyan-400/70 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                placeholder="Search concepts (e.g. 'RRF', 'abstention', 'hash', 'SHA')..."
                className="w-full bg-white/[0.06] hover:bg-white/[0.09] focus:bg-black/50 border border-white/10 focus:border-cyan-400/60 rounded-xl pl-9 pr-10 py-2 text-xs text-white placeholder-slate-400 transition-all outline-none backdrop-blur-md shadow-inner"
              />
              {inputVal ? (
                <button
                  type="button"
                  onClick={handleClear}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              ) : (
                <kbd className="hidden sm:inline-block absolute right-3 top-1/2 -translate-y-1/2 text-[9px] font-mono text-slate-400 bg-white/5 border border-white/10 px-1.5 py-0.5 rounded">
                  Enter
                </kbd>
              )}
            </form>

            {/* Quick Demo Preset Pills & Cluster Filter */}
            <div className="hidden sm:flex items-center space-x-1.5 overflow-x-auto text-[10px]">
              <span className="text-slate-500 font-mono flex items-center space-x-1 shrink-0">
                <Compass className="w-3 h-3 text-cyan-400" />
                <span>Tracer:</span>
              </span>
              {SAMPLE_SEARCH_PRESETS.map((preset) => (
                <button
                  key={preset.query}
                  onClick={() => executeSearch(preset.query)}
                  className={`px-2 py-0.5 rounded-full transition-all border whitespace-nowrap ${
                    searchQuery === preset.query
                      ? "bg-cyan-500/20 text-cyan-300 border-cyan-400/50 shadow-sm shadow-cyan-500/20"
                      : "bg-white/[0.03] hover:bg-white/10 text-slate-400 hover:text-slate-200 border-white/5"
                  }`}
                >
                  {preset.label}
                </button>
              ))}
              <span className="text-slate-600 px-1">|</span>
              <button
                onClick={() => setActiveCluster(null)}
                className={`px-2 py-0.5 rounded-full transition-all border whitespace-nowrap ${
                  activeCluster === null
                    ? "bg-white/10 text-white border-white/20"
                    : "text-slate-400 hover:text-white border-transparent"
                }`}
              >
                All Clusters
              </button>
              {Object.entries(CLUSTER_COLOR_MAP).slice(0, 3).map(([clusterId, meta]) => (
                <button
                  key={clusterId}
                  onClick={() => setActiveCluster(clusterId === activeCluster ? null : clusterId)}
                  className={`px-2 py-0.5 rounded-full transition-all border whitespace-nowrap flex items-center space-x-1 ${
                    activeCluster === clusterId
                      ? "bg-white/15 text-white border-white/30"
                      : "text-slate-400 hover:text-slate-200 border-white/5"
                  }`}
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: meta.hex }} />
                  <span className="truncate max-w-[90px]">{meta.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Controls: Mode & Status */}
          <div className="flex items-center space-x-2 shrink-0">
            {isSearching && (
              <div className="hidden lg:flex items-center space-x-1.5 text-xs font-mono text-cyan-300 bg-cyan-950/70 border border-cyan-400/40 px-2.5 py-1 rounded-xl animate-pulse">
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                <span>Path Active ({searchPath.length} hops)</span>
              </div>
            )}

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
          <div className="flex items-center justify-between pb-3.5 border-b border-white/10">
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

          {/* Active Knowledge Path Banner */}
          {isSearching && searchPath.length > 0 && (
            <div className="mt-3 bg-gradient-to-r from-cyan-950/60 to-blue-950/40 border border-cyan-400/40 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-cyan-300 font-semibold flex items-center space-x-1.5">
                  <Zap className="w-3.5 h-3.5 text-cyan-400 animate-bounce" />
                  <span>Knowledge Tracer Route</span>
                </span>
                <button
                  onClick={handleClear}
                  className="text-[10px] text-slate-400 hover:text-white underline font-mono"
                >
                  Reset Path
                </button>
              </div>

              {/* Breadcrumb Steps */}
              <div className="flex flex-wrap items-center gap-1 text-[11px] text-slate-300">
                {searchPath.map((nodeId, idx) => {
                  const pathNode = nodes.find((n) => n.id === nodeId);
                  const isEnd = idx === searchPath.length - 1;
                  return (
                    <React.Fragment key={nodeId}>
                      <span
                        className={`px-1.5 py-0.5 rounded font-mono text-[10px] ${
                          isEnd
                            ? "bg-cyan-500/20 text-cyan-200 border border-cyan-400/40 font-bold"
                            : "bg-white/5 text-slate-300"
                        }`}
                      >
                        {pathNode ? pathNode.label.slice(0, 16) + "..." : nodeId}
                      </span>
                      {idx < searchPath.length - 1 && (
                        <ChevronRight className="w-3 h-3 text-cyan-400/60" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          )}

          {/* Node Metadata & Context Content */}
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
              <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                {nodes.map((node) => {
                  const inPath = searchPath.includes(node.id);
                  return (
                    <button
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all flex items-center justify-between border ${
                        node.id === activeNode.id
                          ? "bg-cyan-500/15 border-cyan-400/40 text-cyan-200"
                          : inPath
                          ? "bg-cyan-950/30 border-cyan-500/20 text-cyan-300"
                          : "bg-white/[0.02] border-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
                      }`}
                    >
                      <div className="flex items-center space-x-1.5 truncate pr-2">
                        {inPath && <CheckCircle2 className="w-3 h-3 text-cyan-400 shrink-0" />}
                        <span className="truncate">{node.label}</span>
                      </div>
                      <span className="text-[9px] font-mono opacity-60">L{node.level}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Footer Stats */}
          <div className="pt-4 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex items-center space-x-1.5">
              <Network className="w-3.5 h-3.5 text-cyan-400" />
              <span>{links.length} Connected Links</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Tracer Active</span>
            </div>
          </div>
        </div>
      }
    >
      {/* Mounted Full-Bleed 3D WebGL Force Graph Canvas with Tracer Pulse */}
      <DocumentGraph />
    </Layout>
  );
};

export default App;
