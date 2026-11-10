import { useMemo } from "react";
import * as THREE from "three";

export interface ClusterMeta {
  hex: string;
  varName: string;
  name: string;
  threeColor: THREE.Color;
}

export const CLUSTER_COLOR_MAP: Record<string, { hex: string; varName: string; name: string }> = {
  cluster_foundation: {
    hex: "#00f5ff",
    varName: "var(--glow-cyan)",
    name: "Foundation & Architecture",
  },
  cluster_ingestion: {
    hex: "#00ff88",
    varName: "var(--glow-green)",
    name: "Ingestion & Provenance",
  },
  cluster_retrieval: {
    hex: "#00f5ff",
    varName: "var(--glow-cyan)",
    name: "Hybrid Semantic Retrieval",
  },
  cluster_verification: {
    hex: "#ff007f",
    varName: "var(--glow-magenta)",
    name: "Evidence Verification & NLI",
  },
  cluster_graph: {
    hex: "#9d4edd",
    varName: "var(--glow-purple)",
    name: "Knowledge Graph",
  },
  cluster_agent: {
    hex: "#ff9900",
    varName: "var(--glow-amber)",
    name: "Autonomous Research Agent",
  },
};

export const LEVEL_RADIUS_MAP: Record<number, number> = {
  0: 16,  // Level 0: Central Sun (Paper Root)
  1: 9.5, // Level 1: Major Planets (H1 Sections)
  2: 5.5, // Level 2: Moons (H2 Subsections)
  3: 3.5, // Level 3: Satellites (Flashcards / Atomic Concepts)
};

export const LEVEL_ORBIT_DISTANCE: Record<number, number> = {
  1: 190, // Root to H1 link distance
  2: 80,  // H1 to H2 link distance
  3: 35,  // H2 to Flashcard link distance
};

export function getClusterColor(clusterId: string): string {
  return CLUSTER_COLOR_MAP[clusterId]?.hex || "#00f5ff";
}

export function getClusterThreeColor(clusterId: string): THREE.Color {
  const hex = getClusterColor(clusterId);
  return new THREE.Color(hex);
}

export function getNodeRadius(level: number): number {
  return LEVEL_RADIUS_MAP[level] ?? 5;
}

export function useClusterColor(clusterId: string) {
  return useMemo(() => {
    const entry = CLUSTER_COLOR_MAP[clusterId] || {
      hex: "#00f5ff",
      varName: "var(--glow-cyan)",
      name: "General Topic",
    };
    return {
      ...entry,
      threeColor: new THREE.Color(entry.hex),
    };
  }, [clusterId]);
}
