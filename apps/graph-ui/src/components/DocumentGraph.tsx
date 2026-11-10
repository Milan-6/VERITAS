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
import mockTreeRaw from "../data/mock_document_tree.json";

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
  ctx.shadowBlur = 12;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const spriteMaterial = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
  });

  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.scale.set(40, 10, 1);
  return sprite;
}

export const DocumentGraph: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fg3dRef = useRef<ForceGraph3DMethods<DocumentTreeNode, DocumentTreeLink>>();
  const fg2dRef = useRef<ForceGraph2DMethods<DocumentTreeNode, DocumentTreeLink>>();

  const [dimensions, setDimensions] = useState({
    width: typeof window !== "undefined" ? window.innerWidth : 1200,
    height: typeof window !== "undefined" ? window.innerHeight : 800,
  });

  const {
    dimension,
    selectedNode,
    setSelectedNode,
    hoveredNode,
    setHoveredNode,
    activeCluster,
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
    const rawNodes = mockTreeRaw.nodes as DocumentTreeNode[];
    const rawLinks = mockTreeRaw.links as DocumentTreeLink[];

    const clonedNodes: DocumentTreeNode[] = rawNodes.map((n) => {
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

    const clonedLinks: DocumentTreeLink[] = rawLinks.map((l) => ({ ...l }));

    return {
      nodes: clonedNodes,
      links: clonedLinks,
    };
  }, []);

  // Configure D3 Physics Simulation (The "Solar System" effect)
  const configurePhysics = useCallback(
    (fgInstance: any) => {
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
          // Stronger spring tension for satellite clusters to orbit as a cohesive group
          return maxL === 3 ? 0.85 : 0.45;
        });
      }

      // Reheat simulation smoothly
      fgInstance.d3ReheatSimulation();
    },
    []
  );

  useEffect(() => {
    if (dimension === "3d" && fg3dRef.current) {
      configurePhysics(fg3dRef.current);
    } else if (dimension === "2d" && fg2dRef.current) {
      configurePhysics(fg2dRef.current);
    }
  }, [dimension, graphData, configurePhysics]);

  // Custom 3D Node Mesh Generator
  const nodeThreeObject = useCallback(
    (node: DocumentTreeNode) => {
      const radius = getNodeRadius(node.level);
      const hexColor = getClusterColor(node.topic_cluster);
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isFilteredOut = activeCluster !== null && node.topic_cluster !== activeCluster;

      const group = new THREE.Group();

      // 1. Primary Solid Sphere Mesh
      const geometry = new THREE.SphereGeometry(radius, 24, 24);
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(hexColor),
        roughness: 0.15,
        metalness: 0.8,
        emissive: new THREE.Color(hexColor),
        emissiveIntensity: isSelected
          ? 1.2
          : isHovered
          ? 0.9
          : node.level === 0
          ? 0.75
          : isFilteredOut
          ? 0.1
          : 0.35,
        transparent: isFilteredOut,
        opacity: isFilteredOut ? 0.25 : 1.0,
      });

      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      // 2. Solar Corona / Orbital Atmosphere Ring for Root, H1, or Active Nodes
      if (node.level === 0 || node.level === 1 || isSelected || isHovered) {
        const ringGeo = new THREE.RingGeometry(radius * 1.3, radius * 1.55, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(hexColor),
          side: THREE.DoubleSide,
          transparent: true,
          opacity: isSelected ? 0.7 : isHovered ? 0.5 : node.level === 0 ? 0.45 : 0.25,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 3;
        group.add(ring);
      }

      // 3. Floating Text Label Sprite (Levels 0, 1, or Active Selection)
      if (node.level <= 1 || isSelected || isHovered) {
        const labelText =
          node.label.length > 32 ? node.label.slice(0, 30) + "..." : node.label;
        const sprite = createTextSprite(
          labelText,
          hexColor,
          node.level === 0 ? 32 : 24
        );
        sprite.position.set(0, radius + 8, 0);
        group.add(sprite);
      }

      return group;
    },
    [selectedNode, hoveredNode, activeCluster]
  );

  // Custom 2D Canvas Node Renderer
  const nodeCanvasObject = useCallback(
    (node: DocumentTreeNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const radius = getNodeRadius(node.level);
      const hexColor = getClusterColor(node.topic_cluster);
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isFilteredOut = activeCluster !== null && node.topic_cluster !== activeCluster;

      const x = node.x || 0;
      const y = node.y || 0;

      ctx.save();
      ctx.globalAlpha = isFilteredOut ? 0.2 : 1.0;

      // Glow halo on hover or selection
      if (isSelected || isHovered || node.level === 0) {
        ctx.beginPath();
        ctx.arc(x, y, radius * 1.4, 0, 2 * Math.PI, false);
        ctx.fillStyle = `${hexColor}33`;
        ctx.fill();
      }

      // Solid Node Body
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = hexColor;
      ctx.shadowColor = hexColor;
      ctx.shadowBlur = isSelected ? 20 : isHovered ? 15 : 8;
      ctx.fill();

      // Border Ring
      ctx.lineWidth = isSelected ? 2.5 : 1.2;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();

      // Text label for Level 0, 1, or when zoomed in
      if (node.level <= 1 || isSelected || isHovered || globalScale > 1.5) {
        const label =
          node.label.length > 28 ? node.label.slice(0, 26) + "..." : node.label;
        const fontSize = Math.max(10, Math.min(14, 12 / globalScale));
        ctx.font = `600 ${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = "#ffffff";
        ctx.shadowColor = "#000000";
        ctx.shadowBlur = 4;
        ctx.fillText(label, x, y + radius + 4);
      }

      ctx.restore();
    },
    [selectedNode, hoveredNode, activeCluster]
  );

  // Node Interaction: Smooth Camera Zoom to Selected Node
  const handleNodeClick = useCallback(
    (node: DocumentTreeNode) => {
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
          1200 // Camera transition in milliseconds
        );
      } else if (dimension === "2d" && fg2dRef.current && node.x !== undefined && node.y !== undefined) {
        fg2dRef.current.centerAt(node.x, node.y, 1000);
        fg2dRef.current.zoom(2.2, 1000);
      }
    },
    [setSelectedNode, dimension]
  );

  // Background Click: Reset selection and zoom out to fit all nodes
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    if (dimension === "3d" && fg3dRef.current) {
      fg3dRef.current.zoomToFit(1000, 60);
    } else if (dimension === "2d" && fg2dRef.current) {
      fg2dRef.current.zoomToFit(1000, 60);
    }
  }, [setSelectedNode, dimension]);

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
          onNodeHover={(node: any) => setHoveredNode(node || null)}
          onBackgroundClick={handleBackgroundClick}
          
          // Link Styling & Neural Pulse Particles
          linkColor={(link: any) => {
            const targetCluster =
              typeof link.target === "object" ? link.target.topic_cluster : "";
            const hex = getClusterColor(targetCluster);
            return `${hex}44`; // 25% opacity for subtle orbital lines
          }}
          linkWidth={1.2}
          linkDirectionalParticles={1}
          linkDirectionalParticleSpeed={0.0035}
          linkDirectionalParticleWidth={1.8}
          linkDirectionalParticleColor={(link: any) => {
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
          onNodeHover={(node: any) => setHoveredNode(node || null)}
          onBackgroundClick={handleBackgroundClick}
          linkColor={(link: any) => {
            const targetCluster =
              typeof link.target === "object" ? link.target.topic_cluster : "";
            const hex = getClusterColor(targetCluster);
            return `${hex}44`;
          }}
          linkWidth={1.2}
          linkDirectionalParticles={1}
          linkDirectionalParticleSpeed={0.0035}
          linkDirectionalParticleWidth={1.8}
          linkDirectionalParticleColor={(link: any) => {
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
