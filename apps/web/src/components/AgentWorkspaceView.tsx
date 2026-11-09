"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  Sparkles,
  Terminal,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Search,
  BookOpen,
  FileText,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  Loader2,
  Check,
  XCircle,
  HelpCircle,
} from "lucide-react";
import { api } from "../lib/api";
import { AgentEvent, VerificationReport, DocumentItem } from "../types";

interface AgentWorkspaceViewProps {
  documents: DocumentItem[];
}

const EXAMPLE_PROMPTS = [
  "Analyze empirical trade-offs across sparse attention mechanisms and transformers.",
  "Compare quantitative evaluation results and benchmark accuracies across papers.",
  "Identify methodological limitations and future research gaps in the workspace.",
];

export const AgentWorkspaceView: React.FC<AgentWorkspaceViewProps> = ({ documents }) => {
  const [objective, setObjective] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [verificationReport, setVerificationReport] = useState<VerificationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [expandedClaimDrawer, setExpandedClaimDrawer] = useState(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const handleRunAgent = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!objective.trim() || isRunning) return;

    setIsRunning(true);
    setEvents([]);
    setFinalReport(null);
    setVerificationReport(null);
    setError(null);

    try {
      await api.runAgentTaskStream(
        objective.trim(),
        (ev: AgentEvent) => {
          setEvents((prev) => [...prev, ev]);

          if (ev.status === "completed") {
            if (ev.report) setFinalReport(ev.report);
            if (ev.verification_report) setVerificationReport(ev.verification_report);
          }
        },
        5 // Enforced ceiling: 5 iterations
      );
    } catch (err: any) {
      setError(err?.message || "Autonomous agent workflow encountered a network failure.");
      setEvents((prev) => [
        ...prev,
        {
          status: "error",
          message: err?.message || "Workflow execution interrupted.",
        },
      ]);
    } finally {
      setIsRunning(false);
    }
  };

  const handleReset = () => {
    setEvents([]);
    setFinalReport(null);
    setVerificationReport(null);
    setError(null);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold tracking-widest text-cyan-400 uppercase bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
              Phase 9 Feature
            </span>
            <span className="text-xs text-slate-400">Deterministic ReAct State Machine</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1 flex items-center space-x-2.5">
            <Bot className="w-6 h-6 text-cyan-400" />
            <span>Autonomous AI Research Agent</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Iterative reasoning loop (max 5 steps) • Dynamic tool orchestration • Post-generation claim entailment verification
          </p>
        </div>

        {/* Status Pill */}
        <div className="flex items-center space-x-2 px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isRunning ? "bg-amber-400 animate-pulse" : finalReport ? "bg-emerald-400" : "bg-slate-500"
            }`}
          />
          <span className="text-slate-300">
            {isRunning ? "Agent Active (Streaming)" : finalReport ? "Task Complete" : "Agent Ready"}
          </span>
        </div>
      </div>

      {/* Objective Input Form */}
      <form onSubmit={handleRunAgent} className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
        <label className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>Define Research Objective</span>
        </label>

        <textarea
          rows={3}
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          disabled={isRunning}
          placeholder="What scientific inquiry or multi-paper hypothesis should the agent investigate across your workspace?"
          className="w-full bg-slate-950/90 border border-slate-700/80 rounded-xl p-3.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
        />

        {/* Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] text-slate-500 font-mono">Examples:</span>
          {EXAMPLE_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              type="button"
              disabled={isRunning}
              onClick={() => setObjective(prompt)}
              className="px-2.5 py-1 rounded-lg text-xs bg-slate-950 border border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-cyan-800 transition-colors"
            >
              {prompt.slice(0, 50)}...
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <div className="text-[11px] text-slate-500 font-mono">
            Bound to workspace • Ceiling: 5 iterations • LLM Greedy Decoding (temp=0.0)
          </div>

          <div className="flex items-center space-x-3">
            {events.length > 0 && !isRunning && (
              <button
                type="button"
                onClick={handleReset}
                className="px-3 py-1.5 rounded-xl border border-slate-800 text-slate-400 hover:text-white text-xs font-semibold flex items-center space-x-1.5 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}

            <button
              type="submit"
              disabled={isRunning || !objective.trim()}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-slate-950 font-bold text-xs sm:text-sm flex items-center space-x-2 transition-all shadow-md shadow-cyan-500/10 active:scale-95"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Agent Working...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Execute Research Agent</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Main Execution Split: Live Terminal on left/top, Synthesized Report on right/bottom */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Real-Time Execution Trace Terminal */}
        <div className="lg:col-span-5 bg-[#0A0E1A] border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-[520px]">
          {/* Terminal Title Bar */}
          <div className="px-4 py-3 bg-[#070B14] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>Agent Execution Terminal</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
              <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
            </div>
          </div>

          {/* Terminal Body */}
          <div className="p-4 font-mono text-xs overflow-y-auto flex-1 space-y-3.5">
            {events.length === 0 ? (
              <div className="text-slate-600 text-center py-20 space-y-2">
                <Bot className="w-8 h-8 mx-auto text-slate-700" />
                <p>Agent idle. Enter an objective and launch workflow.</p>
              </div>
            ) : (
              events.map((ev, idx) => (
                <div key={idx} className="space-y-1.5 animate-fadeIn">
                  {ev.status === "thinking" && (
                    <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-cyan-300 space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span className="font-bold text-cyan-400 uppercase">
                          [Step {ev.step || 1}: THINK]
                        </span>
                        {ev.action && <span className="text-slate-500">Plan: {ev.action}</span>}
                      </div>
                      <p className="text-xs text-slate-200 italic leading-relaxed">
                        &ldquo;{ev.thought || ev.message}&rdquo;
                      </p>
                    </div>
                  )}

                  {ev.status === "tool_call" && (
                    <div className="p-2.5 rounded-lg bg-blue-950/40 border border-blue-900/60 text-slate-200 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-bold text-sky-400 uppercase">
                          [Step {ev.step}: ACT ➔ {ev.tool}]
                        </span>
                        {ev.evidence_count !== undefined && (
                          <span className="text-slate-400">{ev.evidence_count} evidence chunks</span>
                        )}
                      </div>
                      {ev.args && (
                        <div className="text-[11px] text-slate-400">
                          Args: <code className="text-slate-300">{JSON.stringify(ev.args)}</code>
                        </div>
                      )}
                      {ev.output_preview && (
                        <div className="p-2 bg-slate-950/80 rounded border border-slate-800/80 text-[11px] text-slate-300 font-sans">
                          {ev.output_preview}
                        </div>
                      )}
                    </div>
                  )}

                  {ev.status === "generating_report" && (
                    <div className="p-2 rounded bg-indigo-950/40 border border-indigo-900/60 text-indigo-300 flex items-center space-x-2 text-[11px]">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{ev.message}</span>
                    </div>
                  )}

                  {ev.status === "verifying" && (
                    <div className="p-2 rounded bg-purple-950/40 border border-purple-900/60 text-purple-300 flex items-center space-x-2 text-[11px]">
                      <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
                      <span>{ev.message}</span>
                    </div>
                  )}

                  {ev.status === "completed" && (
                    <div className="p-2.5 rounded-lg bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 flex items-center space-x-2 text-xs font-bold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>
                        Workflow completed successfully in {ev.steps_taken || 0} iterations.
                      </span>
                    </div>
                  )}

                  {ev.status === "error" && (
                    <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-800/80 text-red-300 flex items-center space-x-2 text-xs">
                      <AlertCircle className="w-4 h-4 text-red-400" />
                      <span>{ev.message}</span>
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>

        {/* Synthesized Research Report & Evidence Verification Card */}
        <div className="lg:col-span-7 space-y-6">
          {finalReport ? (
            <div className="space-y-6">
              {/* Evidence Verification Audit Banner */}
              {verificationReport && (
                <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center space-x-2.5">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <div>
                        <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white">
                          Evidence Entailment Audit
                        </h4>
                        <p className="text-[11px] text-slate-400">
                          Evaluated by Phase 4 Evidence Verification Engine
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-mono font-bold border ${
                          verificationReport.overall_status === "VERIFIED"
                            ? "bg-emerald-950/90 text-emerald-400 border-emerald-800"
                            : verificationReport.overall_status === "PARTIALLY_VERIFIED"
                            ? "bg-amber-950/90 text-amber-400 border-amber-800"
                            : "bg-red-950/90 text-red-400 border-red-800"
                        }`}
                      >
                        {verificationReport.overall_status === "VERIFIED"
                          ? "100% Entailed"
                          : verificationReport.overall_status === "PARTIALLY_VERIFIED"
                          ? "Partially Verified"
                          : "Unverified Claims"}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Supported</div>
                      <div className="text-base font-bold text-emerald-400 font-mono">
                        {verificationReport.supported_count}
                      </div>
                    </div>
                    <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Contradicted</div>
                      <div className="text-base font-bold text-red-400 font-mono">
                        {verificationReport.contradicted_count}
                      </div>
                    </div>
                    <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Missing Evid.</div>
                      <div className="text-base font-bold text-amber-400 font-mono">
                        {verificationReport.missing_count}
                      </div>
                    </div>
                  </div>

                  {/* Toggle Claims Drawer */}
                  <button
                    onClick={() => setExpandedClaimDrawer(!expandedClaimDrawer)}
                    className="w-full py-2 text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center justify-center space-x-1 border-t border-slate-800/80 pt-3"
                  >
                    <span>{expandedClaimDrawer ? "Hide Atomic Claims" : "Inspect Atomic Claims"}</span>
                    {expandedClaimDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {expandedClaimDrawer && (
                    <div className="space-y-2.5 max-h-60 overflow-y-auto pt-2">
                      {verificationReport.claims.map((claim, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{claim.claim_text}</span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                                claim.status === "SUPPORTED"
                                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                                  : claim.status === "CONTRADICTED"
                                  ? "bg-red-950 text-red-400 border border-red-800"
                                  : "bg-amber-950 text-amber-400 border border-amber-800"
                              }`}
                            >
                              {claim.status}
                            </span>
                          </div>

                          {claim.source_excerpt && (
                            <blockquote className="p-2 bg-slate-900/80 rounded border border-slate-800/80 text-[11px] text-slate-300 italic font-serif">
                              &ldquo;{claim.source_excerpt}&rdquo;
                            </blockquote>
                          )}

                          {claim.document_title && (
                            <div className="text-[10px] text-slate-500 font-mono">
                              Grounding: {claim.document_title} (p. {claim.page_number})
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Synthesized Markdown Report Card */}
              <div className="p-6 sm:p-8 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
                    <FileText className="w-4 h-4" />
                    <span>Synthesized Research Report</span>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">Grounded Markdown</span>
                </div>

                <div className="prose prose-invert prose-sm max-w-none space-y-4 text-slate-300 leading-relaxed font-sans">
                  {finalReport.split("\n\n").map((paragraph, pIdx) => {
                    if (paragraph.startsWith("# ")) {
                      return (
                        <h2 key={pIdx} className="text-lg font-bold text-white pt-2 border-b border-slate-800 pb-1">
                          {paragraph.replace("# ", "")}
                        </h2>
                      );
                    }
                    if (paragraph.startsWith("## ")) {
                      return (
                        <h3 key={pIdx} className="text-sm font-bold text-cyan-300 pt-1">
                          {paragraph.replace("## ", "")}
                        </h3>
                      );
                    }
                    if (paragraph.startsWith("- ")) {
                      return (
                        <ul key={pIdx} className="list-disc pl-5 space-y-1 text-xs">
                          {paragraph.split("\n").map((line, lIdx) => (
                            <li key={lIdx}>{line.replace("- ", "")}</li>
                          ))}
                        </ul>
                      );
                    }
                    return (
                      <p key={pIdx} className="text-xs leading-relaxed">
                        {paragraph}
                      </p>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-2xl text-slate-500 text-xs space-y-3">
              <BookOpen className="w-10 h-10 mx-auto text-slate-700" />
              <h3 className="text-sm font-bold text-slate-300">No Report Generated Yet</h3>
              <p className="max-w-md mx-auto leading-relaxed">
                Define an objective and launch the agent. The ReAct state machine will search your workspace, inspect sections, synthesize findings, and evaluate claim entailment.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
