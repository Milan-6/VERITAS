"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  FileText,
  Bookmark,
  ChevronRight,
  ChevronDown,
  X,
  ExternalLink,
  Bot,
  User as UserIcon,
  CheckCircle2,
  AlertTriangle,
  Hash,
  Layers,
  Search,
} from "lucide-react";
import { ChatSession, ChatMessage, Citation, DocumentItem } from "../types";
import { api } from "../lib/api";

interface ResearchStudioViewProps {
  documents: DocumentItem[];
  onOpenUpload: () => void;
}

export const ResearchStudioView: React.FC<ResearchStudioViewProps> = ({
  documents,
  onOpenUpload,
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [selectedDocFilter, setSelectedDocFilter] = useState<string>("");
  
  // Provenance drawer inspection state
  const [inspectedCitation, setInspectedCitation] = useState<Citation | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  // Load chat sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setIsLoadingSessions(true);
      const data = await api.listChatSessions();
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        selectSession(data[0].id);
      } else if (data.length === 0) {
        createNewSession();
      }
    } catch (err) {
      console.error("Failed to load chat sessions:", err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const selectSession = async (sessionId: string) => {
    setActiveSessionId(sessionId);
    try {
      const detail = await api.getChatSession(sessionId);
      setMessages(detail.messages || []);
    } catch (err) {
      console.error("Failed to fetch session messages:", err);
    }
  };

  const createNewSession = async () => {
    try {
      const newSess = await api.createChatSession(
        "New Research Inquiry",
        selectedDocFilter || undefined
      );
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setMessages([]);
    } catch (err) {
      console.error("Failed to create chat session:", err);
    }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteChatSession(sessionId);
      const updated = sessions.filter((s) => s.id !== sessionId);
      setSessions(updated);
      if (activeSessionId === sessionId) {
        if (updated.length > 0) {
          selectSession(updated[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to delete chat session:", err);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isSending) return;

    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      try {
        const s = await api.createChatSession(inputQuery.slice(0, 32));
        setSessions((prev) => [s, ...prev]);
        targetSessionId = s.id;
        setActiveSessionId(s.id);
      } catch {
        return;
      }
    }

    const tempUserMsg: ChatMessage = {
      id: "temp-" + Date.now(),
      session_id: targetSessionId,
      role: "user",
      content: inputQuery,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    const queryToSend = inputQuery;
    setInputQuery("");
    setIsSending(true);

    try {
      const res = await api.sendChatMessage(targetSessionId, queryToSend);
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, res]);
    } catch (err: any) {
      const errorAssistantMsg: ChatMessage = {
        id: "err-" + Date.now(),
        session_id: targetSessionId,
        role: "assistant",
        content: `Error generating research answer: ${err.message}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorAssistantMsg]);
    } finally {
      setIsSending(false);
    }
  };

  // Render message text with interactive citation pills
  const renderGroundedContent = (content: string, citations?: Citation[] | null) => {
    if (!citations || citations.length === 0) {
      return <p className="whitespace-pre-line leading-relaxed">{content}</p>;
    }

    // Split text on citation pattern [Document: X, Page: Y]
    const citationRegex = /(\[Document:\s*[^,]+,\s*Page:\s*\d+\])/g;
    const parts = content.split(citationRegex);

    return (
      <div className="whitespace-pre-line leading-relaxed space-y-1">
        {parts.map((part, index) => {
          if (citationRegex.test(part)) {
            // Find citation matching page number or title
            const pageMatch = part.match(/Page:\s*(\d+)/i);
            const pageNum = pageMatch ? parseInt(pageMatch[1], 10) : undefined;
            const matchedCitation = citations.find(
              (c) => pageNum !== undefined && c.page_number === pageNum
            ) || citations[0];

            return (
              <button
                key={index}
                onClick={() => setInspectedCitation(matchedCitation)}
                className="inline-flex items-center space-x-1 mx-1 px-2 py-0.5 rounded-md bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 text-[11px] font-mono font-medium transition-colors shadow-subtle group"
              >
                <Bookmark className="w-3 h-3 text-amber-600 group-hover:scale-110 transition-transform" />
                <span>{part}</span>
              </button>
            );
          }
          return <span key={index}>{part}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col lg:flex-row gap-6 h-[calc(100vh-8.5rem)] max-w-7xl mx-auto w-full">
      {/* Left: Chat Sessions History (Sidebar) */}
      <div className="w-full lg:w-64 bg-panel border border-border rounded-2xl p-4 flex flex-col shadow-subtle shrink-0">
        <button
          onClick={createNewSession}
          className="w-full flex items-center justify-center space-x-2 bg-ink-900 hover:bg-ink-700 text-white py-2 px-3 rounded-xl text-xs font-medium transition-colors shadow-subtle mb-3"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Research Thread</span>
        </button>

        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          {isLoadingSessions ? (
            <p className="text-xs text-ink-400 text-center py-4">Loading sessions...</p>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-ink-400 text-center py-4">No sessions yet.</p>
          ) : (
            sessions.map((sess) => (
              <div
                key={sess.id}
                onClick={() => selectSession(sess.id)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-xs transition-colors flex items-center justify-between group cursor-pointer border ${
                  activeSessionId === sess.id
                    ? "bg-veritas-50 text-veritas-700 border-veritas-200 font-semibold"
                    : "text-ink-700 hover:bg-surface-subtle border-transparent"
                }`}
              >
                <div className="flex items-center space-x-2 truncate pr-2">
                  <MessageSquare className="w-3.5 h-3.5 shrink-0 text-ink-400 group-hover:text-ink-600" />
                  <span className="truncate">{sess.title || "Research Inquiry"}</span>
                </div>
                <button
                  onClick={(e) => deleteSession(sess.id, e)}
                  title="Delete session"
                  className="opacity-0 group-hover:opacity-100 text-ink-400 hover:text-rose-600 p-1 rounded transition-opacity"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Center: Conversation Stream */}
      <div className="flex-1 bg-panel border border-border rounded-2xl flex flex-col shadow-subtle overflow-hidden relative">
        {/* Chat Header Bar */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-surface-subtle">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-veritas-600" />
            <h2 className="text-xs font-semibold text-ink-900 uppercase tracking-wider">
              Grounded Research Studio
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              Deterministic Provenance
            </span>
          </div>

          {/* Scope Document Filter */}
          <select
            value={selectedDocFilter}
            onChange={(e) => setSelectedDocFilter(e.target.value)}
            className="text-xs bg-panel border border-border rounded-lg px-2.5 py-1 text-ink-700 focus:outline-none focus:border-veritas-500 max-w-[180px] truncate"
          >
            <option value="">All Uploaded Documents</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="text-center py-16 space-y-3 max-w-md mx-auto">
              <div className="w-10 h-10 rounded-2xl bg-veritas-50 text-veritas-600 border border-veritas-100 flex items-center justify-center mx-auto shadow-subtle">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-ink-900">Ask anything across your research corpus</h3>
              <p className="text-xs text-ink-500 leading-relaxed">
                Every factual claim is backed by hybrid vector search (Dense + BM25) and verified with page-level citations. Click any citation badge to view source evidence.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-start space-x-3 text-xs ${
                  msg.role === "user" ? "flex-row-reverse space-x-reverse" : ""
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    msg.role === "user"
                      ? "bg-ink-900 text-white"
                      : "bg-veritas-50 text-veritas-600 border border-veritas-100"
                  }`}
                >
                  {msg.role === "user" ? <UserIcon className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div
                  className={`max-w-2xl rounded-2xl p-4 shadow-subtle border ${
                    msg.role === "user"
                      ? "bg-ink-900 text-white border-transparent"
                      : "bg-panel text-ink-900 border-border"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    renderGroundedContent(msg.content, msg.citations)
                  ) : (
                    <p className="whitespace-pre-line leading-relaxed">{msg.content}</p>
                  )}

                  {/* Verification / Citations Footer */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border flex flex-wrap items-center gap-1.5 text-[11px] text-ink-500">
                      <span className="font-semibold text-ink-700">Verified Sources:</span>
                      {msg.citations.map((c, i) => (
                        <button
                          key={i}
                          onClick={() => setInspectedCitation(c)}
                          className="px-2 py-0.5 rounded bg-surface-subtle hover:bg-surface-hover text-ink-700 border border-border text-[10px] font-mono transition-colors"
                        >
                          Page {c.page_number} ({c.document_title || "Paper"})
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {isSending && (
            <div className="flex items-center space-x-3 text-xs text-ink-500 animate-pulse">
              <div className="w-7 h-7 rounded-full bg-veritas-50 text-veritas-600 flex items-center justify-center border border-veritas-100">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="bg-panel border border-border rounded-xl px-4 py-2.5">
                Executing hybrid retrieval & verifying provenance citations...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Query Input Bar */}
        <form onSubmit={handleSendMessage} className="p-4 border-t border-border bg-surface-subtle flex items-center space-x-2">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask a scientific question grounded in your papers..."
            className="flex-1 bg-panel border border-border rounded-xl px-4 py-2.5 text-xs text-ink-900 placeholder-ink-400 focus:outline-none focus:border-veritas-500 transition-colors shadow-subtle"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isSending}
            className="bg-ink-900 hover:bg-ink-700 disabled:opacity-50 text-white p-2.5 rounded-xl transition-colors shadow-subtle shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* Right Drawer: Cryptographic Provenance Inspector */}
      {inspectedCitation && (
        <div className="w-full lg:w-80 bg-panel border border-border rounded-2xl shadow-floating p-5 flex flex-col shrink-0 animate-fadeIn space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <h3 className="text-xs font-semibold text-ink-900 uppercase tracking-wider">Provenance Inspector</h3>
            </div>
            <button onClick={() => setInspectedCitation(null)} className="text-ink-400 hover:text-ink-700">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto text-xs">
            <div>
              <span className="text-[10px] font-mono text-ink-400 uppercase tracking-wider block">Document</span>
              <p className="font-semibold text-ink-900 mt-0.5">{inspectedCitation.document_title || "Unknown Document"}</p>
            </div>

            <div className="grid grid-cols-2 gap-2 bg-surface-subtle p-3 rounded-xl border border-border text-[11px]">
              <div>
                <span className="text-ink-400">Page Number</span>
                <p className="font-bold text-ink-900">Page {inspectedCitation.page_number}</p>
              </div>
              <div>
                <span className="text-ink-400">Section</span>
                <p className="font-bold text-ink-900 truncate">{inspectedCitation.section_title || "Body"}</p>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-ink-400 uppercase tracking-wider block">
                Verbatim Extracted Chunk
              </span>
              <div className="bg-surface-subtle p-3.5 rounded-xl border border-border text-xs text-ink-700 leading-relaxed whitespace-pre-line font-serif italic">
                "{inspectedCitation.chunk_text || inspectedCitation.source_excerpt || "No verbatim text recorded."}"
              </div>
            </div>

            {inspectedCitation.chunk_id && (
              <div>
                <span className="text-[10px] font-mono text-ink-400 uppercase tracking-wider block">Chunk ID</span>
                <span className="inline-flex items-center space-x-1 font-mono text-[10px] text-ink-500 bg-surface-subtle px-2 py-0.5 rounded border border-border mt-1">
                  <Hash className="w-3 h-3 text-veritas-gold" />
                  <span className="truncate">{inspectedCitation.chunk_id}</span>
                </span>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-border">
            <button
              onClick={() => setInspectedCitation(null)}
              className="w-full py-2 bg-surface-subtle hover:bg-surface-hover text-ink-700 rounded-xl text-xs font-medium transition-colors border border-border"
            >
              Close Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
