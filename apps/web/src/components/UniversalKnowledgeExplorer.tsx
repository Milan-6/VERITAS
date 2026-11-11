"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import ForceGraph3D, { ForceGraphMethods as ForceGraph3DMethods } from "react-force-graph-3d";
import ForceGraph2D, { ForceGraphMethods as ForceGraph2DMethods } from "react-force-graph-2d";
import * as THREE from "three";
import {
  Compass,
  Search,
  Zap,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  Layers,
  Network,
  Cpu,
  RefreshCw,
  X,
  Eye,
  Sliders,
  FileText,
  ListTree,
  ShieldCheck,
} from "lucide-react";
import { useKnowledgeStore, GraphNode, GraphLink } from "../store/useKnowledgeStore";

const CLUSTER_HEX: Record<string, string> = {
  cluster_foundation: "#2563EB", // Primary Prussian Blue
  cluster_ingestion: "#059669",  // Emerald
  cluster_retrieval: "#D97706",  // Warm Gold
  cluster_evaluation: "#7C3AED", // Violet
  cluster_security: "#DC2626",   // Ruby
  cluster_verification: "#0D9488", // Teal
};

export const UniversalKnowledgeExplorer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fg3dRef = useRef<ForceGraph3DMethods<GraphNode, GraphLink>>();
  const fg2dRef = useRef<ForceGraph2DMethods<GraphNode, GraphLink>>();

  const {
    documentId,
    filename,
    nodes,
    links,
    hierarchy,
    evidence,
    selectedNode,
    setSelectedNode,
    searchQuery,
    setSearchQuery,
    searchPath,
    dimension,
    setDimension,
    dataSource,
    resetToFallback,
  } = useKnowledgeStore();

  const [activeTab, setActiveTab] = useState<"hierarchy" | "evidence" | "inspector">("hierarchy");
  const [isEngineIdle, setIsEngineIdle] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Update canvas size
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 800,
          height: containerRef.current.clientHeight || 600,
        });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Whenever nodes or links change, restart simulation force layout
  useEffect(() => {
    if (fg3dRef.current) {
      fg3dRef.current.d3ReheatSimulation();
      // Animate camera to center
      fg3dRef.current.cameraPosition({ x: 0, y: 0, z: 280 }, { x: 0, y: 0, z: 0 }, 1000);
    }
    if (fg2dRef.current) {
      fg2dRef.current.d3ReheatSimulation();
      fg2dRef.current.zoomToFit(400, 40);
    }
    setIsEngineIdle(false);
  }, [nodes, links]);

  // Node radius by hierarchy level (L0: 16, L1: 10, L2: 6, L3: 4)
  const getNodeRadius = (lvl: number) => {
    if (lvl === 0) return 16;
    if (lvl === 1) return 10;
    if (lvl === 2) return 6;
    return 3.8;
  };

  // Custom Three.js 3D Sphere Object with glowing rings & state reactivity
  const nodeThreeObject = useCallback(
    (node: GraphNode) => {
      const r = getNodeRadius(node.level);
      const color = CLUSTER_HEX[node.topic_cluster] || "#2563EB";
      const isSelected = selectedNode?.id === node.id;
      const inPath = searchPath.length > 0 ? searchPath.includes(node.id) : true;

      const group = new THREE.Group();

      // Sphere with physical gloss
      const geometry = new THREE.SphereGeometry(r, 24, 24);
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(color),
        roughness: 0.25,
        metalness: 0.8,
        emissive: new THREE.Color(color),
        emissiveIntensity: isSelected ? 0.95 : 0.2,
        transparent: true,
        opacity: inPath ? 1.0 : 0.2,
      });

      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      // Orbital highlight ring for selected or root
      if (node.level <= 1 || isSelected) {
        const ringGeo = new THREE.RingGeometry(r * 1.3, r * 1.5, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(isSelected ? "#F59E0B" : color),
          side: THREE.DoubleSide,
          transparent: true,
          opacity: isSelected ? 0.85 : 0.35,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 3;
        group.add(ring);
      }

      return group;
    },
    [selectedNode, searchPath]
  );

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-4rem)] bg-canvas overflow-hidden">
      {/* 3D WebGL Canvas Area */}
      <div className="flex-1 relative h-full flex flex-col min-w-0" ref={containerRef}>
        
        {/* Floating Controls Bar */}
        <div className="absolute top-4 left-4 right-4 z-10 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
          {/* Search Field */}
          <div className="pointer-events-auto flex items-center bg-panel/90 backdrop-blur-md border border-border rounded-xl px-3 py-1.5 shadow-subtle max-w-sm w-full">
            <Search className="w-4 h-4 text-ink-400 mr-2 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search concepts across hierarchy..."
              className="bg-transparent text-xs text-ink-900 placeholder-ink-400 focus:outline-none w-full"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="text-ink-400 hover:text-ink-700 ml-1">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Active Document Indicator, Dimension Toggle & GPU Indicator */}
          <div className="pointer-events-auto flex items-center space-x-2">
            {filename && (
              <div className="bg-panel/90 backdrop-blur-md border border-border rounded-xl px-3 py-1 text-[11px] font-medium text-ink-700 shadow-subtle flex items-center space-x-1.5 truncate max-w-xs">
                <FileText className="w-3.5 h-3.5 text-veritas-600 shrink-0" />
                <span className="truncate">{filename}</span>
              </div>
            )}

            <div className="bg-panel/90 backdrop-blur-md border border-border rounded-xl px-2.5 py-1 text-[11px] font-mono text-ink-500 shadow-subtle flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-veritas-600" />
              <span>{isEngineIdle ? "GPU IDLE" : "60 FPS"}</span>
            </div>

            <div className="bg-panel/90 backdrop-blur-md border border-border rounded-xl p-1 shadow-subtle flex items-center space-x-1 text-xs">
              <button
                onClick={() => setDimension("2d")}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                  dimension === "2d" ? "bg-veritas-50 text-veritas-700 font-semibold" : "text-ink-500 hover:text-ink-900"
                }`}
              >
                2D
              </button>
              <button
                onClick={() => setDimension("3d")}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                  dimension === "3d" ? "bg-veritas-50 text-veritas-700 font-semibold" : "text-ink-500 hover:text-ink-900"
                }`}
              >
                3D WebGL
              </button>
            </div>
          </div>
        </div>

        {/* Canvas Engine */}
        <div className="w-full h-full cursor-grab active:cursor-grabbing bg-[#0A0D14]">
          {dimension === "3d" ? (
            <ForceGraph3D
              ref={fg3dRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={{ nodes, links }}
              backgroundColor="#0A0D14"
              nodeThreeObject={nodeThreeObject}
              onNodeClick={(node: GraphNode) => setSelectedNode(node)}
              onEngineStop={() => setIsEngineIdle(true)}
              linkColor={() => "#2A364F"}
              linkWidth={1.2}
              linkDirectionalParticles={1}
              linkDirectionalParticleSpeed={0.005}
              linkDirectionalParticleColor={() => "#D97706"}
              warmupTicks={50}
              cooldownTicks={120}
            />
          ) : (
            <ForceGraph2D
              ref={fg2dRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={{ nodes, links }}
              backgroundColor="#0A0D14"
              nodeColor={(node: GraphNode) => CLUSTER_HEX[node.topic_cluster] || "#2563EB"}
              nodeRelSize={4}
              onNodeClick={(node: GraphNode) => setSelectedNode(node)}
              onEngineStop={() => setIsEngineIdle(true)}
              linkColor={() => "#2A364F"}
              linkWidth={1.2}
            />
          )}
        </div>
      </div>

      {/* Right Drawer: Hierarchy, Evidence & Concept Inspector */}
      <div className="w-full lg:w-96 bg-panel border-t lg:border-t-0 lg:border-l border-border h-full flex flex-col shadow-card z-20">
        {/* Drawer Tabs */}
        <div className="p-3 border-b border-border flex items-center justify-between bg-surface-subtle">
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setActiveTab("hierarchy")}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 ${
                activeTab === "hierarchy" ? "bg-panel text-veritas-700 shadow-sm font-semibold" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              <ListTree className="w-3.5 h-3.5" />
              <span>Hierarchy ({hierarchy.length || nodes.length})</span>
            </button>
            <button
              onClick={() => setActiveTab("evidence")}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 ${
                activeTab === "evidence" ? "bg-panel text-veritas-700 shadow-sm font-semibold" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Evidence ({evidence.length})</span>
            </button>
            <button
              onClick={() => setActiveTab("inspector")}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 ${
                activeTab === "inspector" ? "bg-panel text-veritas-700 shadow-sm font-semibold" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Inspector</span>
            </button>
          </div>
          {dataSource === "live" && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              Live
            </span>
          )}
        </div>

        {/* Tab 1: Hierarchy Tree (L0-L3) */}
        {activeTab === "hierarchy" && (
          <div className="p-4 flex-1 overflow-y-auto space-y-2">
            <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-wider mb-2">
              Extracted Document Hierarchy (L0 - L3)
            </div>
            {hierarchy.length > 0 ? (
              <div className="space-y-1.5">
                {hierarchy.map((item) => {
                  const isSelected = selectedNode?.id === item.id;
                  const indentClass =
                    item.level === 0 ? "pl-2" : item.level === 1 ? "pl-5" : item.level === 2 ? "pl-8" : "pl-11";

                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        const target = nodes.find((n) => n.id === item.id);
                        if (target) {
                          setSelectedNode(target);
                          setActiveTab("inspector");
                        }
                      }}
                      className={`w-full text-left py-2 pr-3 rounded-lg text-xs transition-colors flex items-center justify-between border ${indentClass} ${
                        isSelected
                          ? "bg-veritas-50 text-veritas-700 border-veritas-200 font-semibold"
                          : "border-transparent text-ink-700 hover:bg-surface-subtle"
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{
                            backgroundColor:
                              item.level === 0
                                ? "#2563EB"
                                : item.level === 1
                                ? "#059669"
                                : item.level === 2
                                ? "#D97706"
                                : "#7C3AED",
                          }}
                        />
                        <span className="truncate">{item.title}</span>
                      </div>
                      <span className="text-[10px] font-mono text-ink-400 shrink-0 ml-2">
                        {item.level_name.split(" ")[0]} • P{item.page}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="space-y-1.5">
                {nodes.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => {
                      setSelectedNode(n);
                      setActiveTab("inspector");
                    }}
                    className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-surface-subtle text-ink-700 flex items-center justify-between"
                  >
                    <span className="truncate">{n.label}</span>
                    <span className="text-[10px] font-mono text-ink-400">L{n.level}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Evidence Stream */}
        {activeTab === "evidence" && (
          <div className="p-4 flex-1 overflow-y-auto space-y-3">
            <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-wider mb-2">
              Verified Evidence Payload ({evidence.length})
            </div>
            {evidence.length > 0 ? (
              evidence.map((ev) => (
                <div key={ev.id} className="p-3 bg-surface-subtle rounded-xl border border-border space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-ink-500 font-medium">
                    <span className="truncate max-w-[180px] font-semibold text-ink-800">{ev.section}</span>
                    <span className="font-mono text-[10px] bg-panel px-1.5 py-0.5 rounded border border-border">
                      Page {ev.page}
                    </span>
                  </div>
                  <p className="text-xs text-ink-700 leading-relaxed">{ev.text}</p>
                </div>
              ))
            ) : (
              <div className="p-6 text-center text-xs text-ink-400">
                No standalone evidence chunks found for this view.
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Concept Inspector */}
        {activeTab === "inspector" && (
          <div className="p-5 flex-1 overflow-y-auto space-y-5">
            {selectedNode ? (
              <>
                <div>
                  <div className="flex items-center space-x-2 mb-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: CLUSTER_HEX[selectedNode.topic_cluster] || "#2563EB" }}
                    />
                    <span className="text-xs text-ink-500 font-medium capitalize">
                      {selectedNode.topic_cluster.replace("cluster_", "")}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-subtle text-ink-500 border border-border ml-auto">
                      Level {selectedNode.level}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-ink-900 leading-snug">{selectedNode.label}</h3>
                </div>

                <div className="bg-surface-subtle rounded-xl p-4 border border-border space-y-2">
                  <span className="text-[10px] font-mono text-ink-400 uppercase tracking-wider block">
                    Evidence Payload / Excerpt
                  </span>
                  <p className="text-xs text-ink-700 leading-relaxed whitespace-pre-line">
                    {selectedNode.panel_payload}
                  </p>
                </div>

                {/* Connected Relationships */}
                <div>
                  <span className="text-[11px] font-semibold text-ink-500 block mb-2 uppercase tracking-wider">
                    Connected Graph Links
                  </span>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {links
                      .filter(
                        (l) =>
                          (typeof l.source === "object" ? l.source.id : l.source) === selectedNode.id ||
                          (typeof l.target === "object" ? l.target.id : l.target) === selectedNode.id
                      )
                      .map((l, idx) => {
                        const sId = typeof l.source === "object" ? l.source.id : l.source;
                        const tId = typeof l.target === "object" ? l.target.id : l.target;
                        const otherId = sId === selectedNode.id ? tId : sId;
                        const otherNode = nodes.find((n) => n.id === otherId);

                        return (
                          <button
                            key={idx}
                            onClick={() => otherNode && setSelectedNode(otherNode)}
                            className="w-full text-left px-3 py-1.5 rounded-lg text-xs bg-panel border border-border hover:bg-surface-subtle flex items-center justify-between text-ink-700"
                          >
                            <span className="truncate pr-2">{otherNode?.label || otherId}</span>
                            <span className="text-[10px] font-mono text-veritas-600">
                              {l.relationship || "linked"}
                            </span>
                          </button>
                        );
                      })}
                  </div>
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-xs text-ink-400 flex flex-col items-center justify-center space-y-2">
                <Network className="w-8 h-8 text-ink-300" />
                <p>Select a node on the canvas to inspect its scientific context.</p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="p-4 border-t border-border bg-surface-subtle flex items-center justify-between text-xs text-ink-500">
          <span>{links.length} Connected Links • {nodes.length} Nodes</span>
          {dataSource === "live" && (
            <button
              onClick={resetToFallback}
              className="text-ink-400 hover:text-ink-700 text-[11px] underline"
            >
              Reset Default
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
