"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

interface OrganicSculpture3DProps {
  className?: string;
  intensity?: "ambient" | "active" | "processing";
  goldTint?: boolean;
}

export const OrganicSculpture3D: React.FC<OrganicSculpture3DProps> = ({
  className = "w-full h-48",
  intensity = "ambient",
  goldTint = true,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 300;
    const height = container.clientHeight || 200;

    // Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 4.5);

    // Renderer with soft anti-aliased output
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    // Parametric Torus Knot (Metallic Flower / Ribbon Structure)
    const geometry = new THREE.TorusKnotGeometry(1.0, 0.28, 128, 32, 2, 3);
    
    // Store original position coordinates for deformation
    const positionAttribute = geometry.attributes.position;
    const originalPositions = positionAttribute.clone();

    // Luxurious Brushed Metal Material
    const material = new THREE.MeshStandardMaterial({
      color: goldTint ? new THREE.Color("#E5A93C") : new THREE.Color("#3B82F6"),
      metalness: 0.88,
      roughness: 0.22,
      emissive: goldTint ? new THREE.Color("#78350F") : new THREE.Color("#1E3A8A"),
      emissiveIntensity: intensity === "processing" ? 0.35 : 0.12,
      wireframe: false,
    });

    const sculpture = new THREE.Mesh(geometry, material);
    scene.add(sculpture);

    // Lighting: Studio key, fill, and rim lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff7ed, 2.5);
    keyLight.position.set(5, 5, 5);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(goldTint ? 0xfbbf24 : 0x60a5fa, 3.0, 20);
    rimLight.position.set(-5, -3, 2);
    scene.add(rimLight);

    // Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const speedMultiplier = intensity === "processing" ? 1.8 : intensity === "active" ? 1.0 : 0.45;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime() * speedMultiplier;

      // Smooth rhythmic rotation
      sculpture.rotation.x = elapsedTime * 0.35;
      sculpture.rotation.y = elapsedTime * 0.45;

      // Subtle parametric wave deformation (Organic floral breathing)
      const pos = geometry.attributes.position;
      const count = pos.count;
      for (let i = 0; i < count; i++) {
        const ox = originalPositions.getX(i);
        const oy = originalPositions.getY(i);
        const oz = originalPositions.getZ(i);

        const wave = Math.sin(elapsedTime * 2.0 + ox * 3.0 + oy * 2.0) * (intensity === "processing" ? 0.08 : 0.035);
        pos.setXYZ(i, ox * (1 + wave), oy * (1 + wave), oz * (1 + wave));
      }
      pos.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, [intensity, goldTint]);

  return <div ref={mountRef} className={`relative overflow-hidden pointer-events-none ${className}`} />;
};
