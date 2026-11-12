/**
 * VERITAS WebGL Graph UI Data Contract
 * Strict TypeScript interfaces representing hierarchical academic document structures.
 */

export type NodeLevel = 0 | 1 | 2 | 3;
// 0: Root (Paper Title)
// 1: H1 (Major Section)
// 2: H2 (Subsection / Technical Methodology)
// 3: Flashcard (Atomic Concept / QA / Definition)

export interface DocumentTreeNode {
  id: string;
  label: string;
  level: NodeLevel;
  topic_cluster: string;
  panel_payload: string;
  
  // Dynamic WebGL simulation properties (populated by force layout engine)
  x?: number;
  y?: number;
  z?: number;
  vx?: number;
  vy?: number;
  vz?: number;
  fx?: number;
  fy?: number;
  fz?: number;
  val?: number;
  color?: string;
}

export interface DocumentTreeLink {
  source: string | DocumentTreeNode;
  target: string | DocumentTreeNode;
  relationship?: string;
}

export interface DocumentTreeData {
  nodes: DocumentTreeNode[];
  links: DocumentTreeLink[];
}
