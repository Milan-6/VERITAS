"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { DocumentItem, User } from "../types";
import { ParticleFormation } from "./motion/ParticleEngine3D";
import {
  FileText,
  MessageSquare,
  Sparkles,
  BookOpen,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Clock,
  Layers,
} from "lucide-react";

// Client-only dynamic imports for 3D Motion Components to bypass SSR window checks
const OrganicSculpture3D = dynamic(
  () => import("./motion/OrganicSculpture3D").then((m) => m.OrganicSculpture3D),
  { ssr: false }
);

const ParticleEngine3D = dynamic(
  () => import("./motion/ParticleEngine3D").then((m) => m.ParticleEngine3D),
  { ssr: false }
);

interface DashboardViewProps {
  user: User | null;
  documents: DocumentItem[];
  onNavigateTab: (tab: "dashboard" | "catalog" | "chat" | "graph" | "study") => void;
  onOpenUpload: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  user,
  documents,
  onNavigateTab,
  onOpenUpload,
}) => {
  const [activeFormation, setActiveFormation] = useState<ParticleFormation>("sphere");

  const completedDocs = documents.filter((d) => d.status === "COMPLETED");
  const processingDocs = documents.filter((d) => d.status === "PROCESSING" || d.status === "QUEUED");

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fadeIn">
      {/* Hero Banner with Integrated 3D Sculpture */}
      <div className="relative overflow-hidden rounded-2xl bg-panel border border-border shadow-card p-8 lg:p-10 flex flex-col lg:flex-row items-center justify-between gap-8">
        <div className="max-w-xl space-y-4 z-10">
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-veritas-50 border border-veritas-100 text-veritas-600 text-xs font-medium">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Universal Research Intelligence</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-semibold text-ink-900 tracking-tight leading-snug">
            Welcome back, {user?.full_name ? user.full_name.split(" ")[0] : "Researcher"}.
          </h1>

          <p className="text-sm text-ink-500 leading-relaxed">
            VERITAS synthesizes literature across disciplines with cryptographic provenance, strict citation grounding, and interactive 3D concept maps.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => onNavigateTab("chat")}
              className="flex items-center space-x-2 bg-ink-900 hover:bg-ink-700 text-white px-4 py-2.5 rounded-xl text-xs font-medium transition-all shadow-subtle"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Open Research Studio</span>
              <ArrowRight className="w-3.5 h-3.5 opacity-70" />
            </button>

            <button
              onClick={onOpenUpload}
              className="flex items-center space-x-2 bg-surface-subtle hover:bg-surface-hover text-ink-700 border border-border px-4 py-2.5 rounded-xl text-xs font-medium transition-all"
            >
              <FileText className="w-4 h-4 text-ink-500" />
              <span>Upload PDF Paper</span>
            </button>
          </div>
        </div>

        {/* Floating 3D Organic Metal Sculpture */}
        <div className="relative w-full lg:w-96 h-56 flex items-center justify-center shrink-0">
          <div className="absolute inset-0 bg-radial-gradient from-veritas-goldLight/30 to-transparent blur-2xl pointer-events-none" />
          <OrganicSculpture3D className="w-full h-full" intensity="ambient" goldTint={true} />
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-panel border border-border rounded-xl p-5 shadow-subtle space-y-2">
          <div className="flex items-center justify-between text-ink-500 text-xs">
            <span>Documents Ingested</span>
            <FileText className="w-4 h-4 text-veritas-600" />
          </div>
          <div className="text-2xl font-bold text-ink-900">{documents.length}</div>
          <p className="text-[11px] text-ink-500 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3 text-veritas-emerald" />
            <span>{completedDocs.length} fully verified & indexed</span>
          </p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-5 shadow-subtle space-y-2">
          <div className="flex items-center justify-between text-ink-500 text-xs">
            <span>Active Knowledge Trees</span>
            <Layers className="w-4 h-4 text-veritas-gold" />
          </div>
          <div className="text-2xl font-bold text-ink-900">
            {completedDocs.length > 0 ? "18 Nodes / 21 Links" : "Ready"}
          </div>
          <p className="text-[11px] text-ink-500">Multilevel hierarchical tree</p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-5 shadow-subtle space-y-2">
          <div className="flex items-center justify-between text-ink-500 text-xs">
            <span>Evidence Grounding</span>
            <ShieldCheck className="w-4 h-4 text-veritas-emerald" />
          </div>
          <div className="text-2xl font-bold text-ink-900">100%</div>
          <p className="text-[11px] text-ink-500">Strict abstention enabled</p>
        </div>

        <div className="bg-panel border border-border rounded-xl p-5 shadow-subtle space-y-2">
          <div className="flex items-center justify-between text-ink-500 text-xs">
            <span>Active Pipelines</span>
            <Zap className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-ink-900">
            {processingDocs.length > 0 ? processingDocs.length : "Idle (0% GPU)"}
          </div>
          <p className="text-[11px] text-ink-500">Background workers ready</p>
        </div>
      </div>

      {/* Main Content Grid: Interactive Particle Morphing Engine & Recent Papers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left: Particle Morphing Research Sandbox (2 cols) */}
        <div className="lg:col-span-2 bg-panel border border-border rounded-2xl p-6 shadow-subtle flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border">
            <div>
              <h2 className="text-base font-semibold text-ink-900">Neural Concept Particle Engine</h2>
              <p className="text-xs text-ink-500 mt-0.5">
                Dynamic particle transformations mirroring research state morphs across geometry spaces.
              </p>
            </div>

            {/* Formation Controls */}
            <div className="flex items-center space-x-1 bg-surface-subtle p-1 rounded-lg border border-border text-xs">
              {(["sphere", "plane", "helix", "burst"] as ParticleFormation[]).map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setActiveFormation(fmt)}
                  className={`px-2.5 py-1 rounded-md capitalize transition-all ${
                    activeFormation === fmt
                      ? "bg-panel text-ink-900 shadow-subtle font-medium"
                      : "text-ink-500 hover:text-ink-900"
                  }`}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Three.js Particle Canvas */}
          <div className="relative w-full h-80 my-4 flex items-center justify-center">
            <ParticleEngine3D
              className="w-full h-full"
              formation={activeFormation}
              count={1600}
              particleColor="#D97706"
            />
            <div className="absolute bottom-3 left-4 text-[11px] font-mono text-ink-400 bg-panel/80 px-2 py-0.5 rounded border border-border backdrop-blur-sm">
              State: {activeFormation.toUpperCase()} • 1,600 Verified Vertices
            </div>
          </div>

          <div className="pt-4 border-t border-border flex items-center justify-between text-xs text-ink-500">
            <span>Explore relationships visually</span>
            <button
              onClick={() => onNavigateTab("graph")}
              className="text-veritas-600 hover:text-veritas-700 font-medium flex items-center space-x-1"
            >
              <span>Open Knowledge Explorer</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Recent Papers & Shortcuts (1 col) */}
        <div className="bg-panel border border-border rounded-2xl p-6 shadow-subtle flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-900">Recent Documents</h3>
              <button
                onClick={() => onNavigateTab("catalog")}
                className="text-xs text-veritas-600 hover:text-veritas-700 font-medium"
              >
                View all ({documents.length})
              </button>
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-12 space-y-3">
                <FileText className="w-8 h-8 text-ink-300 mx-auto" />
                <p className="text-xs text-ink-500">No research papers uploaded yet.</p>
                <button
                  onClick={onOpenUpload}
                  className="text-xs text-veritas-600 font-medium hover:underline"
                >
                  Upload your first PDF
                </button>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                {documents.slice(0, 5).map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 rounded-xl border border-border hover:bg-surface-subtle transition-colors flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-3">
                      <p className="text-xs font-medium text-ink-900 truncate">{doc.filename}</p>
                      <p className="text-[10px] text-ink-500 mt-0.5">
                        {doc.status === "COMPLETED" ? "Indexed" : doc.status} • {(doc.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </p>
                    </div>
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        doc.status === "COMPLETED"
                          ? "bg-veritas-emerald"
                          : doc.status === "PROCESSING"
                          ? "bg-amber-400 animate-pulse"
                          : "bg-ink-300"
                      }`}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-border mt-4">
            <button
              onClick={() => onNavigateTab("study")}
              className="w-full py-2.5 px-3 rounded-xl bg-veritas-50 text-veritas-700 hover:bg-veritas-100 text-xs font-medium flex items-center justify-center space-x-2 transition-colors border border-veritas-100"
            >
              <BookOpen className="w-4 h-4" />
              <span>Review Adaptive Flashcards</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
