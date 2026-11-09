"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  FileText,
  Bookmark,
  ChevronRight,
  ExternalLink,
  Bot,
  User as UserIcon,
  BookOpen,
} from "lucide-react";
import { ChatSession, ChatMessage, Citation, DocumentItem } from "../types";
import { api } from "../lib/api";

interface ChatInterfaceProps {
  documents: DocumentItem[];
  onOpenUpload: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ documents, onOpenUpload }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [selectedDocFilter, setSelectedDocFilter] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages
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
    try {
      setActiveSessionId(sessionId);
      const detail = await api.getChatSession(sessionId);
      setMessages(detail.messages || []);
      if (detail.document_id) {
        setSelectedDocFilter(detail.document_id);
      }
    } catch (err) {
      console.error("Failed to load session details:", err);
    }
  };

  const createNewSession = async () => {
    try {
      const newSession = await api.createChatSession(
        "New Research Session",
        selectedDocFilter ? selectedDocFilter : undefined
      );
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessages([]);
    } catch (err) {
      console.error("Failed to create chat session:", err);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    try {
      await api.deleteChatSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = inputQuery.trim();
    if (!query || isSending) return;

    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      try {
        const newSession = await api.createChatSession(
          query.slice(0, 30),
          selectedDocFilter || undefined
        );
        setSessions([newSession, ...sessions]);
        setActiveSessionId(newSession.id);
        targetSessionId = newSession.id;
      } catch (err) {
        console.error("Failed to initialize session before sending:", err);
        return;
      }
    }

    // Optimistic user message rendering
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: targetSessionId,
      role: "user",
      content: query,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setInputQuery("");
    setIsSending(true);

    try {
      const assistantReply = await api.sendChatMessage(targetSessionId, query);
      setMessages((prev) => [...prev, assistantReply]);

      // Update session title locally
      setSessions((prev) =>
        prev.map((s) =>
          s.id === targetSessionId
            ? {
                ...s,
                title:
                  s.title === "New Research Session"
                    ? query.split(" ").slice(0, 5).join(" ") + "..."
                    : s.title,
                message_count: s.message_count + 2,
                updated_at: new Date().toISOString(),
              }
            : s
        )
      );
    } catch (err: any) {
      console.error("Failed to send message:", err);
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        session_id: targetSessionId,
        role: "assistant",
        content: `Error: ${err.message || "Failed to generate grounded response."}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  // Helper to render text with clickable citation badges
  const renderMessageContent = (content: string) => {
    const citationRegex = /\[Document:\s*([^,\]]+),\s*Page:\s*(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.slice(lastIndex, match.index));
      }

      const docTitle = match[1].trim();
      const pageNum = match[2].trim();

      parts.push(
        <span
          key={match.index}
          className="inline-flex items-center space-x-1 mx-1 px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 font-medium align-baseline shadow-sm hover:bg-cyan-900/90 transition-colors cursor-default"
          title={`Evidence Citation: ${docTitle} (Page ${pageNum})`}
        >
          <BookOpen className="w-3 h-3 text-cyan-400 shrink-0 inline" />
          <span>{docTitle}</span>
          <span className="text-cyan-500 font-semibold">• p.{pageNum}</span>
        </span>
      );

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      parts.push(content.slice(lastIndex));
    }

    return parts;
  };

  const isAbstention = (content: string) =>
    content.trim() === "This is not mentioned in the provided research corpus.";

  return (
    <div className="flex h-[740px] rounded-2xl bg-[#090D16] border border-[#1E293B] overflow-hidden shadow-2xl">
      {/* Sidebar: Chat Sessions */}
      <div className="w-72 sm:w-80 border-r border-[#1E293B] bg-[#070A12] flex flex-col shrink-0">
        <div className="p-4 border-b border-[#1E293B] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-slate-200 tracking-wider uppercase font-mono">
                Research Sessions
              </span>
            </div>
            <button
              onClick={createNewSession}
              className="p-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-800/60 text-cyan-400 transition-colors"
              title="New Research Session"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Scope Selector: Document Filter */}
          <div className="space-y-1">
            <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Corpus Scope
            </label>
            <select
              value={selectedDocFilter}
              onChange={(e) => setSelectedDocFilter(e.target.value)}
              className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All Uploaded Literature ({documents.length})</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.metadata?.title || d.filename}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoadingSessions ? (
            <div className="p-4 text-center text-xs text-slate-500 font-mono">
              Loading sessions...
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-6 text-center space-y-2">
              <Bot className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400">No active research sessions.</p>
              <button
                onClick={createNewSession}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300"
              >
                + Start First Session
              </button>
            </div>
          ) : (
            sessions.map((s) => {
              const isActive = s.id === activeSessionId;
              return (
                <div
                  key={s.id}
                  onClick={() => selectSession(s.id)}
                  className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition-all ${
                    isActive
                      ? "bg-cyan-950/40 border border-cyan-800/60 text-cyan-200"
                      : "hover:bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-transparent"
                  }`}
                >
                  <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                    <MessageSquare
                      className={`w-3.5 h-3.5 shrink-0 ${
                        isActive ? "text-cyan-400" : "text-slate-500"
                      }`}
                    />
                    <div className="truncate">
                      <p className="font-medium truncate">{s.title}</p>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(s.updated_at).toLocaleDateString([], {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition-opacity"
                    title="Delete Session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-[#0A0E1A]">
        {/* Chat Header */}
        <div className="h-14 px-6 border-b border-[#1E293B] bg-[#0E1322]/80 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-lg bg-cyan-950/80 border border-cyan-800/80 flex items-center justify-center text-cyan-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-slate-100 tracking-wide">
                  Grounded Evidence Assistant
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 uppercase">
                  Zero Hallucination
                </span>
              </div>
              <p className="text-[10px] text-slate-400">
                Retrieval-Augmented Generation • Strict Citation Attribution
              </p>
            </div>
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-cyan-950/40 border border-cyan-800/40 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/10">
                <Sparkles className="w-6 h-6 text-cyan-400" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-sm font-bold text-slate-200">
                  Ask VERITAS About Your Research Corpus
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Questions are answered strictly using retrieved evidence chunks with exact page
                  citations. Out-of-scope inquiries trigger mandatory abstention.
                </p>
              </div>

              {/* Fast Starter Chips */}
              <div className="w-full space-y-2 pt-2">
                {[
                  "Summarize key findings & methodology across documents",
                  "What specific mathematical models or algorithms are introduced?",
                  "What experimental datasets and benchmark metrics were reported?",
                ].map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputQuery(prompt);
                    }}
                    className="w-full text-left text-xs p-2.5 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 text-slate-300 hover:text-cyan-300 transition-colors flex items-center justify-between group"
                  >
                    <span>{prompt}</span>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-colors shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === "user";
              const isAbstain = !isUser && isAbstention(msg.content);

              return (
                <div
                  key={msg.id}
                  className={`flex items-start space-x-3 ${
                    isUser ? "flex-row-reverse space-x-reverse" : "flex-row"
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
                      isUser
                        ? "bg-slate-800 border-slate-700 text-slate-300"
                        : isAbstain
                        ? "bg-amber-950/40 border-amber-800/60 text-amber-400"
                        : "bg-cyan-950/50 border-cyan-800/60 text-cyan-400"
                    }`}
                  >
                    {isUser ? (
                      <UserIcon className="w-4 h-4" />
                    ) : isAbstain ? (
                      <ShieldAlert className="w-4 h-4 text-amber-400" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-cyan-400" />
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div
                    className={`max-w-[80%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? "bg-cyan-600 text-slate-950 font-medium rounded-tr-none shadow-md shadow-cyan-600/10"
                        : isAbstain
                        ? "bg-amber-950/20 border border-amber-800/40 text-amber-200 rounded-tl-none"
                        : "bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none shadow-md"
                    }`}
                  >
                    {isAbstain ? (
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs uppercase tracking-wider font-mono">
                          <ShieldAlert className="w-3.5 h-3.5" />
                          <span>Strict Abstention Triggered</span>
                        </div>
                        <p className="font-mono text-xs">{msg.content}</p>
                      </div>
                    ) : isUser ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="space-y-3">
                        <div className="whitespace-pre-wrap leading-relaxed">
                          {renderMessageContent(msg.content)}
                        </div>

                        {/* Citation Evidence drawer if present */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                            <span className="text-[10px] font-mono tracking-wider uppercase text-slate-400 flex items-center space-x-1.5">
                              <BookOpen className="w-3 h-3 text-cyan-400" />
                              <span>Attributed Grounding Evidence ({msg.citations.length})</span>
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              {msg.citations.map((c, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 text-[11px] space-y-0.5"
                                >
                                  <p className="font-semibold text-cyan-300 truncate">
                                    {c.document_title}
                                  </p>
                                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                                    <span>p.{c.page_number} • {c.section_title}</span>
                                    {c.score && (
                                      <span className="text-slate-500">
                                        RRF: {c.score.toFixed(3)}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <div
                      className={`text-[10px] mt-2 font-mono ${
                        isUser ? "text-cyan-900" : "text-slate-500"
                      }`}
                    >
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {/* Loading indicator */}
          {isSending && (
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-xl bg-cyan-950/50 border border-cyan-800/60 flex items-center justify-center text-cyan-400 animate-pulse">
                <Bot className="w-4 h-4" />
              </div>
              <div className="rounded-2xl rounded-tl-none p-4 bg-slate-900/90 border border-slate-800 text-xs text-slate-300 flex items-center space-x-2.5 shadow-md">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                <span className="font-mono text-cyan-300">
                  VERITAS is retrieving evidence & synthesizing grounded answer...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-[#1E293B] bg-[#070A12]/80">
          <form onSubmit={handleSendMessage} className="relative flex items-center">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask a question grounded in your research corpus (e.g., 'What were the baseline results?')..."
              disabled={isSending}
              className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-4 pr-12 py-3 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isSending}
              className="absolute right-2 p-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 disabled:opacity-30 disabled:pointer-events-none transition-all"
              title="Send Message"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mt-2 px-1">
            <span>Powered by VERITAS Hybrid Retrieval & Deterministic Decoding</span>
            <span>Temperature: 0.0 • Strict Grounding</span>
          </div>
        </div>
      </div>
    </div>
  );
};
