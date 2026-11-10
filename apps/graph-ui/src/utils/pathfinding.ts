import { DocumentTreeNode } from "../data/types";

export interface PathResult {
  nodeIds: string[];
  links: any[];
}

export function getNodeId(item: any): string {
  if (typeof item === "string") return item;
  if (item && typeof item === "object" && item.id) return String(item.id);
  return String(item);
}

/**
 * Breadth-First Search (BFS) pathfinder across graph links
 * Returns the exact sequence of nodes and connecting links from root to target.
 */
export function findHierarchyPath(
  nodes: DocumentTreeNode[],
  links: any[],
  rootId: string = "node_root",
  targetId: string
): PathResult {
  if (rootId === targetId) {
    return { nodeIds: [rootId], links: [] };
  }

  // Build undirected adjacency graph
  const adj = new Map<string, Array<{ neighbor: string; link: any }>>();
  for (const n of nodes) {
    adj.set(n.id, []);
  }

  for (const l of links) {
    const sId = getNodeId(l.source);
    const tId = getNodeId(l.target);
    if (!adj.has(sId)) adj.set(sId, []);
    if (!adj.has(tId)) adj.set(tId, []);
    adj.get(sId)!.push({ neighbor: tId, link: l });
    adj.get(tId)!.push({ neighbor: sId, link: l });
  }

  // Queue-based BFS
  const queue: string[] = [rootId];
  const visited = new Set<string>([rootId]);
  const parentMap = new Map<string, { parent: string; link: any }>();

  let found = false;
  while (queue.length > 0) {
    const curr = queue.shift()!;
    if (curr === targetId) {
      found = true;
      break;
    }

    const neighbors = adj.get(curr) || [];
    for (const { neighbor, link } of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        parentMap.set(neighbor, { parent: curr, link });
        queue.push(neighbor);
      }
    }
  }

  if (!found) {
    return { nodeIds: [], links: [] };
  }

  // Reconstruct path from target back to root
  const pathNodeIds: string[] = [];
  const pathLinks: any[] = [];

  let curr = targetId;
  pathNodeIds.push(curr);

  while (curr !== rootId && parentMap.has(curr)) {
    const { parent, link } = parentMap.get(curr)!;
    pathLinks.unshift(link);
    curr = parent;
    pathNodeIds.unshift(curr);
  }

  return {
    nodeIds: pathNodeIds,
    links: pathLinks,
  };
}
