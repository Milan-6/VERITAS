import React, { useRef, useEffect, useMemo, useState, useCallback } from "react";
import ForceGraph3D, { ForceGraphMethods as ForceGraph3DMethods } from "react-force-graph-3d";
import ForceGraph2D, { ForceGraphMethods as ForceGraph2DMethods } from "react-force-graph-2d";
import * as THREE from "three";
import { useGraphStore } from "../store/useGraphStore";
import { DocumentTreeNode, DocumentTreeLink } from "../data/types";
import {
  getClusterColor,
  getNodeRadius,
} from "../hooks/useClusterColor";
import { getNodeId } from "../utils/pathfinding";

/**
 * Creates a high-resolution 2D Canvas Text Sprite for WebGL node labels in 3D space
 */
function createTextSprite(text: string, colorHex: string, fontSize: number = 28): THREE.Sprite {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d")!;
  canvas.width = 512;
  canvas.height = 128;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = `600 ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  // Text Glow Effect
  ctx.shadowColor = colorHex;
  ctx.shadowBlur = 14;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const spriteMaterial = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
  });

  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.scale.set(42, 10.5, 1);
  return sprite;
}

/**
 * Checks if a graph link directly connects two consecutive nodes in the active knowledge path
 */
function isLinkInPath(link: any, searchPath: string[]): boolean {
  if (!searchPath || searchPath.length < 2) return false;
  const s = getNodeId(link.source);
  const t = getNodeId(link.target);

  for (let i = 0; i < searchPath.length - 1; i++) {
    const a = searchPath[i];
    const b = searchPath[i + 1];
    if ((s === a && t === b) || (s === b && t === a)) {
      return true;
    }
  }
  return false;
}

export const DocumentGraph: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fg3dRef = useRef<ForceGraph3DMethods<DocumentTreeNode, DocumentTreeLink>>();
  const fg2dRef = useRef<ForceGraph2DMethods<DocumentTreeNode, DocumentTreeLink>>();
  const idleTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [dimensions, setDimensions] = useState({
    width: typeof window !== "undefined" ? window.innerWidth : 1200,
    height: typeof window !== "undefined" ? window.innerHeight : 800,
  });

  const {
    nodes: storeNodes,
    links: storeLinks,
    dimension,
    selectedNode,
    setSelectedNode,
    hoveredNode,
    setHoveredNode,
    activeCluster,
    isSearching,
    searchPath,
    clearSearch,
    setIsEngineIdle,
  } = useGraphStore();

  // Responsive full-bleed container observer
  useEffect(() => {
    if (!containerRef.current) return;

    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || window.innerWidth,
          height: containerRef.current.clientHeight || window.innerHeight,
        });
      }
    };

    updateDimensions();
    const observer = new ResizeObserver(updateDimensions);
    observer.observe(containerRef.current);
    window.addEventListener("resize", updateDimensions);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateDimensions);
    };
  }, []);

  // Prepare graph data & anchor Level 0 (Root) to the exact celestial center (0, 0, 0)
  const graphData = useMemo(() => {
    const clonedNodes: DocumentTreeNode[] = storeNodes.map((n) => {
      const nodeCopy = { ...n };
      if (nodeCopy.level === 0) {
        // Fix Root node to origin (0, 0, 0) to act as the primary Solar Anchor
        nodeCopy.fx = 0;
        nodeCopy.fy = 0;
        nodeCopy.fz = 0;
        nodeCopy.x = 0;
        nodeCopy.y = 0;
        nodeCopy.z = 0;
      }
      return nodeCopy;
    });

    const clonedLinks: DocumentTreeLink[] = storeLinks.map((l) => ({ ...l }));

    return {
      nodes: clonedNodes,
      links: clonedLinks,
    };
  }, [storeNodes, storeLinks]);

  // ===========================================================================
  // WebGL Render Loop Optimization: Pause on Idle / Zero GPU Drain
  // ===========================================================================
  const wakeRenderLoop = useCallback(() => {
    if (idleTimeoutRef.current) {
      clearTimeout(idleTimeoutRef.current);
      idleTimeoutRef.current = null;
    }
    setIsEngineIdle(false);
    if (dimension === "3d" && fg3dRef.current) {
      fg3dRef.current.resumeAnimation();
    }
  }, [dimension, setIsEngineIdle]);

  const handleEngineStop = useCallback(() => {
    setIsEngineIdle(true);
    // After a 500ms stabilization window, pause continuous WebGL render loop to prevent idle GPU drain
    if (idleTimeoutRef.current) clearTimeout(idleTimeoutRef.current);
    idleTimeoutRef.current = setTimeout(() => {
      if (dimension === "3d" && fg3dRef.current) {
        fg3dRef.current.pauseAnimation();
      }
    }, 500);
  }, [setIsEngineIdle, dimension]);

  // Wake render loop on user viewport events
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleInteraction = () => wakeRenderLoop();
    el.addEventListener("pointerdown", handleInteraction);
    el.addEventListener("wheel", handleInteraction, { passive: true });
    el.addEventListener("touchstart", handleInteraction, { passive: true });

    return () => {
      el.removeEventListener("pointerdown", handleInteraction);
      el.removeEventListener("wheel", handleInteraction);
      el.removeEventListener("touchstart", handleInteraction);
    };
  }, [wakeRenderLoop]);

  // Configure D3 Physics Simulation (The "Solar System" effect)
  const configurePhysics = useCallback((fgInstance: any) => {
    if (!fgInstance) return;

    // 1. Charge Force: Deep repulsion avoiding cluster overlap
    const chargeForce = fgInstance.d3Force("charge");
    if (chargeForce) {
      chargeForce.strength((node: any) => {
        if (node.level === 0) return -1800; // Strong central solar repulsion
        if (node.level === 1) return -700;  // Planetary major body repulsion
        if (node.level === 2) return -300;  // Moon sub-satellite repulsion
        return -120;                        // Flashcard particle repulsion
      });
      chargeForce.distanceMax(800);
    }

    // 2. Link Force: Hierarchy-tiered orbit distances
    const linkForce = fgInstance.d3Force("link");
    if (linkForce) {
      linkForce.distance((link: any) => {
        const sLevel = typeof link.source === "object" ? link.source.level : 0;
        const tLevel = typeof link.target === "object" ? link.target.level : 0;
        const minL = Math.min(sLevel, tLevel);
        const maxL = Math.max(sLevel, tLevel);

        if (minL === 0 && maxL === 1) {
          return 210; // Root to H1: wide primary orbital circumference
        }
        if (minL === 1 && maxL === 2) {
          return 90;  // H1 to H2: planetary moon orbit
        }
        if (minL === 2 && maxL === 3) {
          return 40;  // H2 to Flashcard: compact satellite cluster
        }
        return 120; // Cross-cluster semantic links
      });

      linkForce.strength((link: any) => {
        const maxL = Math.max(
          typeof link.source === "object" ? link.source.level : 0,
          typeof link.target === "object" ? link.target.level : 0
        );
        return maxL === 3 ? 0.85 : 0.45;
      });
    }

    // Reheat simulation smoothly
    fgInstance.d3ReheatSimulation();
  }, []);

  useEffect(() => {
    wakeRenderLoop();
    if (dimension === "3d" && fg3dRef.current) {
      configurePhysics(fg3dRef.current);
    } else if (dimension === "2d" && fg2dRef.current) {
      configurePhysics(fg2dRef.current);
    }
  }, [dimension, graphData, configurePhysics, wakeRenderLoop]);

  // ===========================================================================
  // Tracer Pulse & Camera Tracking Orchestration
  // ===========================================================================
  useEffect(() => {
    if (!isSearching || searchPath.length === 0) return;

    wakeRenderLoop();
    let isCancelled = false;

    const runKnowledgePathSequence = async () => {
      const fg = dimension === "3d" ? fg3dRef.current : fg2dRef.current;
      if (!fg) return;

      const liveNodes = graphData.nodes;
      const liveLinks = graphData.links;

      // Hop sequentially along the nodes in searchPath: [Root, H1, H2, Flashcard]
      for (let i = 0; i < searchPath.length; i++) {
        if (isCancelled) break;
        const nodeId = searchPath[i];
        const nodeObj = liveNodes.find((n: any) => n.id === nodeId);

        if (nodeObj && nodeObj.x !== undefined && nodeObj.y !== undefined) {
          const isFinalTarget = i === searchPath.length - 1;
          const camDistance = isFinalTarget ? 85 : i === 0 ? 220 : 140;

          // Camera navigation
          if (dimension === "3d" && fg3dRef.current) {
            const distRatio = 1 + camDistance / Math.hypot(nodeObj.x, nodeObj.y, nodeObj.z || 0);
            fg3dRef.current.cameraPosition(
              {
                x: nodeObj.x * distRatio,
                y: nodeObj.y * distRatio,
                z: (nodeObj.z || 0) + camDistance,
              },
              { x: nodeObj.x, y: nodeObj.y, z: nodeObj.z || 0 },
              700
            );
          } else if (dimension === "2d" && fg2dRef.current) {
            fg2dRef.current.centerAt(nodeObj.x, nodeObj.y, 700);
            fg2dRef.current.zoom(isFinalTarget ? 3.0 : 1.8, 700);
          }

          // Emit sequential energy particle along the link connecting this node to the next
          if (i < searchPath.length - 1) {
            const nextNodeId = searchPath[i + 1];
            const connectingLink = liveLinks.find((l: any) => {
              const ls = getNodeId(l.source);
              const lt = getNodeId(l.target);
              return (
                (ls === nodeId && lt === nextNodeId) ||
                (ls === nextNodeId && lt === nodeId)
              );
            });

            if (connectingLink && typeof fg.emitParticle === "function") {
              fg.emitParticle(connectingLink);
              setTimeout(() => {
                if (!isCancelled && typeof fg.emitParticle === "function") {
                  fg.emitParticle(connectingLink);
                }
              }, 160);
            }
          }
        }

        await new Promise((r) => setTimeout(r, 750));
      }
    };

    runKnowledgePathSequence();

    return () => {
      isCancelled = true;
    };
  }, [isSearching, searchPath, dimension, graphData, wakeRenderLoop]);

  // ===========================================================================
  // Custom 3D Node Mesh Generator (with LOD Dynamic Scaling & Dimming)
  // ===========================================================================
  const nodeThreeObject = useCallback(
    (node: DocumentTreeNode) => {
      const radius = getNodeRadius(node.level);
      const hexColor = getClusterColor(node.topic_cluster);

      const isPathActive = searchPath.length > 0;
      const isInPath = isPathActive ? searchPath.includes(node.id) : true;
      const isTarget = isPathActive && searchPath[searchPath.length - 1] === node.id;
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isClusterFiltered = activeCluster !== null && node.topic_cluster !== activeCluster;

      const group = new THREE.Group();

      // Visual Dimming: Irrelevant nodes drop to 10% opacity
      const opacity = !isInPath ? 0.10 : isClusterFiltered ? 0.25 : 1.0;
      const emissiveIntensity = !isInPath
        ? 0.05
        : isTarget
        ? 1.8
        : isSelected
        ? 1.3
        : isHovered
        ? 0.95
        : node.level === 0
        ? 0.75
        : 0.35;

      // LOD (Level of Detail) Decision:
      // When zoomed far out, omit text sprites and corona rings for distant Level 2 and Level 3 nodes
      let isFar = false;
      if (fg3dRef.current) {
        const cam = fg3dRef.current.camera();
        if (cam && node.x !== undefined && node.y !== undefined) {
          const dist = cam.position.distanceTo(new THREE.Vector3(node.x, node.y, node.z || 0));
          isFar = dist > 450;
        }
      }

      // 1. Primary Solid Sphere Mesh (Low-poly 16 segments when far, 24 when near)
      const segments = isFar ? 16 : 24;
      const geometry = new THREE.SphereGeometry(radius, segments, segments);
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(hexColor),
        roughness: 0.15,
        metalness: 0.8,
        emissive: new THREE.Color(hexColor),
        emissiveIntensity,
        transparent: true,
        opacity,
      });

      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      // Level of Detail Gating: High-res sprites and corona rings are mounted when close,
      // or unconditionally for Root, H1, selected, hovered, or search path nodes.
      const showHighDetail = isInPath && (node.level <= 1 || isSelected || isHovered || isTarget || !isFar);

      // 2. Solar Corona / Orbital Atmosphere Ring
      if (showHighDetail && (node.level === 0 || node.level === 1 || isSelected || isHovered || isTarget)) {
        const ringGeo = new THREE.RingGeometry(radius * 1.3, radius * 1.6, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(isTarget ? "#ffffff" : hexColor),
          side: THREE.DoubleSide,
          transparent: true,
          opacity: isTarget ? 0.85 : isSelected ? 0.7 : isHovered ? 0.5 : 0.35,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 3;
        group.add(ring);
      }

      // 3. Floating Text Label Sprite
      if (showHighDetail && (node.level <= 1 || isSelected || isHovered || isTarget)) {
        const labelText =
          node.label.length > 32 ? node.label.slice(0, 30) + "..." : node.label;
        const sprite = createTextSprite(
          labelText,
          isTarget ? "#00f5ff" : hexColor,
          isTarget ? 34 : node.level === 0 ? 32 : 24
        );
        sprite.position.set(0, radius + 8, 0);
        group.add(sprite);
      }

      return group;
    },
    [selectedNode, hoveredNode, activeCluster, searchPath]
  );

  // ===========================================================================
  // Custom 2D Canvas Node Renderer
  // ===========================================================================
  const nodeCanvasObject = useCallback(
    (node: DocumentTreeNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const radius = getNodeRadius(node.level);
      const hexColor = getClusterColor(node.topic_cluster);

      const isPathActive = searchPath.length > 0;
      const isInPath = isPathActive ? searchPath.includes(node.id) : true;
      const isTarget = isPathActive && searchPath[searchPath.length - 1] === node.id;
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isClusterFiltered = activeCluster !== null && node.topic_cluster !== activeCluster;

      const x = node.x || 0;
      const y = node.y || 0;

      ctx.save();
      ctx.globalAlpha = !isInPath ? 0.10 : isClusterFiltered ? 0.25 : 1.0;

      // Glow halo on hover, selection, target, or root
      if (isInPath && (isSelected || isHovered || isTarget || node.level === 0)) {
        ctx.beginPath();
        ctx.arc(x, y, radius * 1.5, 0, 2 * Math.PI, false);
        ctx.fillStyle = `${hexColor}33`;
        ctx.fill();
      }

      // Solid Node Body
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = isTarget ? "#ffffff" : hexColor;
      ctx.shadowColor = hexColor;
      ctx.shadowBlur = !isInPath ? 0 : isTarget ? 25 : isSelected ? 20 : isHovered ? 15 : 8;
      ctx.fill();

      // Border Ring
      ctx.lineWidth = isTarget ? 3.0 : isSelected ? 2.5 : 1.2;
      ctx.strokeStyle = isTarget ? "#00f5ff" : "#ffffff";
      ctx.stroke();

      // Text label (LOD: omit distant level 2/3 when scale is low)
      const showText = isInPath && (node.level <= 1 || isSelected || isHovered || isTarget || globalScale > 1.3);
      if (showText) {
        const label =
          node.label.length > 28 ? node.label.slice(0, 26) + "..." : node.label;
        const fontSize = Math.max(10, Math.min(14, 12 / globalScale));
        ctx.font = `600 ${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = isTarget ? "#00f5ff" : "#ffffff";
        ctx.shadowColor = "#000000";
        ctx.shadowBlur = 4;
        ctx.fillText(label, x, y + radius + 4);
      }

      ctx.restore();
    },
    [selectedNode, hoveredNode, activeCluster, searchPath]
  );

  // Node Interaction: Smooth Camera Zoom to Selected Node
  const handleNodeClick = useCallback(
    (node: DocumentTreeNode) => {
      wakeRenderLoop();
      setSelectedNode(node);

      if (dimension === "3d" && fg3dRef.current && node.x !== undefined && node.y !== undefined) {
        const distance = 140;
        const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z || 0);

        fg3dRef.current.cameraPosition(
          {
            x: node.x * distRatio,
            y: node.y * distRatio,
            z: (node.z || 0) + distance,
          },
          { x: node.x, y: node.y, z: node.z || 0 },
          1200
        );
      } else if (dimension === "2d" && fg2dRef.current && node.x !== undefined && node.y !== undefined) {
        fg2dRef.current.centerAt(node.x, node.y, 1000);
        fg2dRef.current.zoom(2.2, 1000);
      }
    },
    [setSelectedNode, dimension, wakeRenderLoop]
  );

  // Background Click: Reset selection and zoom out to fit all nodes
  const handleBackgroundClick = useCallback(() => {
    wakeRenderLoop();
    setSelectedNode(null);
    clearSearch();
    if (dimension === "3d" && fg3dRef.current) {
      fg3dRef.current.zoomToFit(1000, 60);
    } else if (dimension === "2d" && fg2dRef.current) {
      fg2dRef.current.zoomToFit(1000, 60);
    }
  }, [setSelectedNode, clearSearch, dimension, wakeRenderLoop]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative cursor-grab active:cursor-grabbing"
      style={{ width: "100%", height: "100%" }}
    >
      {dimension === "3d" ? (
        <ForceGraph3D
          ref={fg3dRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          backgroundColor="#0a0b10"
          nodeThreeObject={nodeThreeObject}
          nodeLabel={(node: any) =>
            `<div style="background: rgba(10,11,16,0.85); border: 1px solid rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 8px; font-family: sans-serif; backdrop-filter: blur(8px);">
              <div style="font-size: 11px; color: ${getClusterColor(node.topic_cluster)}; font-weight: 700;">Level ${node.level} • ${node.topic_cluster}</div>
              <div style="font-size: 12px; color: #fff; font-weight: 600; margin-top: 2px;">${node.label}</div>
             </div>`
          }
          onNodeClick={handleNodeClick}
          onNodeHover={(node: any) => {
            wakeRenderLoop();
            setHoveredNode(node || null);
          }}
          onNodeDrag={() => wakeRenderLoop()}
          onBackgroundClick={handleBackgroundClick}
          onEngineStop={handleEngineStop}
          
          // Link Styling: Knowledge Path links glow vibrantly; irrelevant links dim to 5%
          linkColor={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            if (searchPath.length > 0) {
              return inPath ? "#00f5ffff" : "#ffffff0d";
            }
            const targetCluster =
              typeof link.target === "object" ? link.target.topic_cluster : "";
            const hex = getClusterColor(targetCluster);
            return `${hex}44`;
          }}
          linkWidth={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 3.5 : 1.0;
          }}
          linkDirectionalParticles={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 3 : 1;
          }}
          linkDirectionalParticleSpeed={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 0.007 : 0.0035;
          }}
          linkDirectionalParticleWidth={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 2.8 : 1.6;
          }}
          linkDirectionalParticleColor={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            if (inPath) return "#00f5ff";
            const targetCluster =
              typeof link.target === "object" ? link.target.topic_cluster : "";
            return getClusterColor(targetCluster);
          }}

          // Simulation Cooling Parameters
          warmupTicks={60}
          cooldownTicks={140}
          d3AlphaDecay={0.022}
          d3VelocityDecay={0.38}
          showNavInfo={false}
        />
      ) : (
        <ForceGraph2D
          ref={fg2dRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          backgroundColor="#0a0b10"
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, getNodeRadius(node.level) + 4, 0, 2 * Math.PI, false);
            ctx.fill();
          }}
          onNodeClick={handleNodeClick}
          onNodeHover={(node: any) => {
            wakeRenderLoop();
            setHoveredNode(node || null);
          }}
          onNodeDrag={() => wakeRenderLoop()}
          onBackgroundClick={handleBackgroundClick}
          onEngineStop={handleEngineStop}
          linkColor={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            if (searchPath.length > 0) {
              return inPath ? "#00f5ffff" : "#ffffff0d";
            }
            const targetCluster =
              typeof link.target === "object" ? link.target.topic_cluster : "";
            const hex = getClusterColor(targetCluster);
            return `${hex}44`;
          }}
          linkWidth={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 3.5 : 1.0;
          }}
          linkDirectionalParticles={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 3 : 1;
          }}
          linkDirectionalParticleSpeed={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 0.007 : 0.0035;
          }}
          linkDirectionalParticleWidth={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            return inPath ? 2.8 : 1.6;
          }}
          linkDirectionalParticleColor={(link: any) => {
            const inPath = isLinkInPath(link, searchPath);
            if (inPath) return "#00f5ff";
            const targetCluster =
              typeof link.target === "object" ? link.target.topic_cluster : "";
            return getClusterColor(targetCluster);
          }}
          warmupTicks={60}
          cooldownTicks={140}
          d3AlphaDecay={0.022}
          d3VelocityDecay={0.38}
        />
      )}
    </div>
  );
};
