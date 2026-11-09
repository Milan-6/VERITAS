"use client";

import React, { useState } from "react";
import {
  Table,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Search,
  Layers,
  ArrowRight,
  ShieldAlert,
  Loader2,
  Info,
} from "lucide-react";
import { DocumentItem, LiteratureMatrix, MatrixColumn } from "../types";
import { api } from "../lib/api";

interface LiteratureMatrixViewProps {
  documents: DocumentItem[];
}

export const LiteratureMatrixView: React.FC<LiteratureMatrixViewProps> = ({ documents }) => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [topicQuery, setTopicQuery] = useState("");
  const [matrix, setMatrix] = useState<LiteratureMatrix | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completedDocs = documents.filter((d) => d.status === "COMPLETED");

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      if (selectedIds.length >= 5) {
        alert("A maximum of 5 documents can be selected for comparison.");
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleGenerate = async () => {
    if (selectedIds.length < 2) {
      setError("Please select at least 2 documents to generate a comparative matrix.");
      return;
    }
    setError(null);
    setIsGenerating(true);
    try {
      const res = await api.generateLiteratureMatrix(selectedIds, topicQuery || undefined);
      setMatrix(res);
    } catch (err: any) {
      setError(err.message || "Failed to generate comparative matrix.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Controls Card */}
      <div className="p-6 rounded-2xl bg-[#0A0E1A] border border-[#1E293B] shadow-xl space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-white tracking-wide flex items-center space-x-2">
              <Table className="w-5 h-5 text-cyan-400" />
              <span>Cross-Paper Comparative Matrix</span>
            </h2>
            <p className="text-xs text-slate-400">
              Select 2 to 5 research papers to synthesize side-by-side and detect empirical contradictions.
            </p>
          </div>

          <div className="text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            Selected: <span className="font-bold text-cyan-400">{selectedIds.length}</span> / 5
          </div>
        </div>

        {/* Paper Selection Checklist */}
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Available Papers ({completedDocs.length})
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 max-h-48 overflow-y-auto p-1">
            {completedDocs.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono col-span-3">
                No completed documents found in workspace. Upload documents first.
              </p>
            ) : (
              completedDocs.map((doc) => {
                const isChecked = selectedIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onClick={() => toggleSelect(doc.id)}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition-all flex items-start space-x-2.5 ${
                      isChecked
                        ? "bg-cyan-950/40 border-cyan-800/80 text-cyan-200"
                        : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="mt-0.5 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 bg-slate-950"
                    />
                    <div className="min-w-0">
                      <p className="font-semibold truncate text-slate-200">
                        {doc.metadata?.title || doc.filename}
                      </p>
                      <span className="text-[10px] font-mono text-slate-500">
                        {doc.metadata?.total_pages || 0} pages • {doc.filename}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Topic Focus Filter & Action */}
        <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-slate-800/80">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={topicQuery}
              onChange={(e) => setTopicQuery(e.target.value)}
              placeholder="Optional focus query (e.g., 'Attention mechanism and benchmark perplexity')..."
              className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={selectedIds.length < 2 || isGenerating}
            className="flex items-center justify-center space-x-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold text-xs px-5 py-2.5 rounded-xl shadow-sm transition-all disabled:opacity-40 disabled:pointer-events-none active:scale-[0.98]"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Generating Matrix...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Compare {selectedIds.length} Papers</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-red-950/30 border border-red-800/50 text-xs text-red-300 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Matrix Display Table */}
      {matrix && (
        <div className="space-y-6">
          {/* Contradictions & Methodological Divergences Banner */}
          {matrix.contradictions_and_divergences && matrix.contradictions_and_divergences.length > 0 && (
            <div className="p-5 rounded-2xl bg-amber-950/20 border border-amber-800/50 space-y-3">
              <div className="flex items-center space-x-2 text-amber-400">
                <AlertTriangle className="w-4 h-4" />
                <h3 className="text-xs font-bold font-mono tracking-wider uppercase">
                  Cross-Paper Divergences & Empirical Contradictions ({matrix.contradictions_and_divergences.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {matrix.contradictions_and_divergences.map((c, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-amber-300 font-mono text-[11px]">
                        {c.aspect}
                      </span>
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                          c.divergence_level === "HIGH"
                            ? "bg-red-950 text-red-400 border border-red-800"
                            : c.divergence_level === "MEDIUM"
                            ? "bg-amber-950 text-amber-400 border border-amber-800"
                            : "bg-blue-950 text-blue-400 border border-blue-800"
                        }`}
                      >
                        {c.divergence_level} Divergence
                      </span>
                    </div>

                    <p className="text-slate-300 leading-relaxed text-[11px] font-medium">
                      {c.description}
                    </p>

                    <div className="flex items-center space-x-2 text-[10px] text-slate-500 font-mono pt-1 border-t border-slate-850">
                      <span className="truncate max-w-[150px]">{c.paper_a_title}</span>
                      <span>vs</span>
                      <span className="truncate max-w-[150px]">{c.paper_b_title}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Side-by-Side Matrix Grid */}
          <div className="rounded-2xl bg-[#0A0E1A] border border-[#1E293B] overflow-hidden shadow-2xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#1E293B] bg-[#0E1424]">
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider font-mono w-48 shrink-0 bg-[#0E1424] sticky left-0 z-20">
                      Scientific Dimension
                    </th>
                    {matrix.columns.map((col) => (
                      <th
                        key={col.document_id}
                        className="p-4 text-xs font-bold text-cyan-300 min-w-[280px] max-w-[340px] border-l border-slate-800/80"
                      >
                        <div className="flex items-center space-x-2">
                          <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                          <span className="truncate">{col.document_title}</span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs text-slate-300">
                  {/* Row 1: Problem Statement */}
                  <tr className="hover:bg-slate-900/30 transition-colors">
                    <td className="p-4 font-bold text-slate-300 font-mono bg-[#0A0E1A] sticky left-0 z-10 border-r border-slate-800/60">
                      1. Problem Statement
                    </td>
                    {matrix.columns.map((col) => (
                      <td key={col.document_id} className="p-4 leading-relaxed border-l border-slate-800/60 font-medium">
                        {col.problem_statement}
                      </td>
                    ))}
                  </tr>

                  {/* Row 2: Methodology */}
                  <tr className="hover:bg-slate-900/30 transition-colors bg-slate-950/20">
                    <td className="p-4 font-bold text-cyan-400 font-mono bg-[#0A0E1A] sticky left-0 z-10 border-r border-slate-800/60">
                      2. Methodology
                    </td>
                    {matrix.columns.map((col) => (
                      <td key={col.document_id} className="p-4 leading-relaxed border-l border-slate-800/60 font-medium text-slate-200">
                        {col.methodology}
                      </td>
                    ))}
                  </tr>

                  {/* Row 3: Datasets Used */}
                  <tr className="hover:bg-slate-900/30 transition-colors">
                    <td className="p-4 font-bold text-sky-400 font-mono bg-[#0A0E1A] sticky left-0 z-10 border-r border-slate-800/60">
                      3. Datasets & Benchmarks
                    </td>
                    {matrix.columns.map((col) => (
                      <td key={col.document_id} className="p-4 leading-relaxed border-l border-slate-800/60 font-medium">
                        {col.dataset_used}
                      </td>
                    ))}
                  </tr>

                  {/* Row 4: Key Results */}
                  <tr className="hover:bg-slate-900/30 transition-colors bg-slate-950/20">
                    <td className="p-4 font-bold text-emerald-400 font-mono bg-[#0A0E1A] sticky left-0 z-10 border-r border-slate-800/60">
                      4. Key Results
                    </td>
                    {matrix.columns.map((col) => (
                      <td key={col.document_id} className="p-4 leading-relaxed border-l border-slate-800/60 font-medium text-emerald-100">
                        {col.key_results}
                      </td>
                    ))}
                  </tr>

                  {/* Row 5: Limitations */}
                  <tr className="hover:bg-slate-900/30 transition-colors">
                    <td className="p-4 font-bold text-rose-400 font-mono bg-[#0A0E1A] sticky left-0 z-10 border-r border-slate-800/60">
                      5. Limitations & Gaps
                    </td>
                    {matrix.columns.map((col) => (
                      <td key={col.document_id} className="p-4 leading-relaxed border-l border-slate-800/60 font-medium text-slate-400">
                        {col.limitations}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
