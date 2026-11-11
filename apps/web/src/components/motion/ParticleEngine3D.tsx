"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export type ParticleFormation = "sphere" | "plane" | "helix" | "burst";

interface ParticleEngineProps {
  className?: string;
  formation?: ParticleFormation;
  count?: number;
  particleColor?: string;
}

export const ParticleEngine3D: React.FC<ParticleEngineProps> = ({
  className = "w-full h-full",
  formation = "sphere",
  count = 1400,
  particleColor = "#D97706", // Restrained warm gold
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const targetPositionsRef = useRef<Float32Array | null>(null);

  // Compute target coordinate formation matrices
  const generateFormationPositions = (type: ParticleFormation, n: number): Float32Array => {
    const arr = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const idx = i * 3;
      if (type === "sphere") {
        // Uniform Fibonacci Sphere Distribution
        const phi = Math.acos(1 - 2 * (i + 0.5) / n);
        const theta = Math.PI * (1 + Math.sqrt(5)) * i;
        const radius = 2.2 + (Math.random() - 0.5) * 0.2;
        arr[idx] = radius * Math.sin(phi) * Math.cos(theta);
        arr[idx + 1] = radius * Math.sin(phi) * Math.sin(theta);
        arr[idx + 2] = radius * Math.cos(phi);
      } else if (type === "plane") {
        // Document page / Matrix sheet
        const cols = Math.floor(Math.sqrt(n));
        const r = Math.floor(i / cols);
        const c = i % cols;
        arr[idx] = (c - cols / 2) * 0.12;
        arr[idx + 1] = (r - cols / 2) * 0.12;
        arr[idx + 2] = (Math.sin(c * 0.2) + Math.cos(r * 0.2)) * 0.15;
      } else if (type === "helix") {
        // Double helix / DNA academic knowledge structure
        const t = (i / n) * Math.PI * 8;
        const strand = i % 2 === 0 ? 1 : -1;
        arr[idx] = Math.cos(t) * 1.5 * strand;
        arr[idx + 1] = (i / n - 0.5) * 5.0;
        arr[idx + 2] = Math.sin(t) * 1.5 * strand;
      } else {
        // Dispersal / Burst
        const r = 0.5 + Math.random() * 4.0;
        const u = Math.random();
        const v = Math.random();
        const theta = u * 2.0 * Math.PI;
        const phi = Math.acos(2.0 * v - 1.0);
        arr[idx] = r * Math.sin(phi) * Math.cos(theta);
        arr[idx + 1] = r * Math.sin(phi) * Math.sin(theta);
        arr[idx + 2] = r * Math.cos(phi);
      }
    }
    return arr;
  };

  useEffect(() => {
    targetPositionsRef.current = generateFormationPositions(formation, count);
  }, [formation, count]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 0, 6.0);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Initial Positions
    const initialPositions = generateFormationPositions("sphere", count);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(initialPositions), 3));

    // Circular particle texture generator
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d")!;
    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, "rgba(255, 255, 255, 1)");
    grad.addColorStop(0.3, particleColor);
    grad.addColorStop(1, "rgba(255, 255, 255, 0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(32, 32, 32, 0, Math.PI * 2);
    ctx.fill();

    const particleTexture = new THREE.CanvasTexture(canvas);

    const material = new THREE.PointsMaterial({
      size: 0.14,
      map: particleTexture,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      blending: THREE.NormalBlending,
    });

    const pointCloud = new THREE.Points(geometry, material);
    scene.add(pointCloud);

    // Render loop with lerp morphing
    let frameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      frameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Gentle rotation
      pointCloud.rotation.y = elapsed * 0.12;
      pointCloud.rotation.x = Math.sin(elapsed * 0.08) * 0.15;

      // Morph current positions toward target positions
      const positions = geometry.attributes.position.array as Float32Array;
      const targets = targetPositionsRef.current;

      if (targets) {
        const lerpFactor = 0.045; // Smooth organic transition
        for (let i = 0; i < positions.length; i++) {
          positions[i] += (targets[i] - positions[i]) * lerpFactor;
        }
        geometry.attributes.position.needsUpdate = true;
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      particleTexture.dispose();
      renderer.dispose();
    };
  }, [count, particleColor]);

  return <div ref={mountRef} className={`relative overflow-hidden pointer-events-none ${className}`} />;
};
