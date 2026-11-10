import { create } from "zustand";
import { DocumentTreeNode } from "../data/types";
import mockTree from "../data/mock_document_tree.json";

interface GraphState {
  // Graph Data
  nodes: DocumentTreeNode[];
  links: Array<{ source: string; target: string }>;
  
  // Selection & Inspector State
  selectedNode: DocumentTreeNode | null;
  hoveredNode: DocumentTreeNode | null;
  
  // Visual Mode
  dimension: "2d" | "3d";
  
  // Filter & Search
  activeCluster: string | null;
  searchQuery: string;

  // Actions
  setSelectedNode: (node: DocumentTreeNode | null) => void;
  setHoveredNode: (node: DocumentTreeNode | null) => void;
  setDimension: (dimension: "2d" | "3d") => void;
  setActiveCluster: (cluster: string | null) => void;
  setSearchQuery: (query: string) => void;
  resetSelection: () => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  nodes: mockTree.nodes as DocumentTreeNode[],
  links: mockTree.links,
  
  selectedNode: null,
  hoveredNode: null,
  dimension: "3d",
  activeCluster: null,
  searchQuery: "",

  setSelectedNode: (node) => set({ selectedNode: node }),
  setHoveredNode: (node) => set({ hoveredNode: node }),
  setDimension: (dimension) => set({ dimension }),
  setActiveCluster: (activeCluster) => set({ activeCluster }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  resetSelection: () => set({ selectedNode: null, hoveredNode: null }),
}));
