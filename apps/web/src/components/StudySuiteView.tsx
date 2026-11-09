"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  BookOpen,
  GraduationCap,
  Download,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  Shuffle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Sparkles,
  Layers,
  FileText,
  AlertCircle,
  ExternalLink,
  Award,
} from "lucide-react";
import { DocumentItem, FlashcardDeck, Flashcard, Quiz, QuizEvaluationResult } from "../types";
import { api } from "../lib/api";

interface StudySuiteViewProps {
  documents: DocumentItem[];
  initialDocumentId?: string | null;
}

export const StudySuiteView: React.FC<StudySuiteViewProps> = ({
  documents,
  initialDocumentId,
}) => {
  const completedDocs = documents.filter((d) => d.status === "COMPLETED");
  const [selectedDocId, setSelectedDocId] = useState<string>(
    initialDocumentId || (completedDocs[0]?.id || "")
  );

  const [activeMode, setActiveMode] = useState<"flashcards" | "quiz">("flashcards");

  // Flashcards state
  const [deck, setDeck] = useState<FlashcardDeck | null>(null);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isLoadingDeck, setIsLoadingDeck] = useState(false);
  const [isExportingAnki, setIsExportingAnki] = useState(false);

  // Quiz state
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [evaluation, setEvaluation] = useState<QuizEvaluationResult | null>(null);
  const [isLoadingQuiz, setIsLoadingQuiz] = useState(false);
  const [isSubmittingQuiz, setIsSubmittingQuiz] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load Deck
  const loadDeck = useCallback(async (docId: string, forceGenerate = false) => {
    if (!docId) return;
    setIsLoadingDeck(true);
    setErrorMsg(null);
    try {
      const data = forceGenerate
        ? await api.generateFlashcards(docId)
        : await api.getFlashcards(docId);
      setDeck(data);
      setCurrentCardIndex(0);
      setIsFlipped(false);
    } catch (err: any) {
      console.error("Error loading flashcards:", err);
      setErrorMsg(err.message || "Failed to load flashcard deck.");
    } finally {
      setIsLoadingDeck(false);
    }
  }, []);

  // Load Quiz
  const loadQuiz = useCallback(async (docId: string, forceGenerate = false) => {
    if (!docId) return;
    setIsLoadingQuiz(true);
    setErrorMsg(null);
    setEvaluation(null);
    setSelectedAnswers({});
    try {
      const data = forceGenerate
        ? await api.generateQuiz(docId)
        : await api.getQuiz(docId);
      setQuiz(data);
    } catch (err: any) {
      console.error("Error loading quiz:", err);
      setErrorMsg(err.message || "Failed to load diagnostic quiz.");
    } finally {
      setIsLoadingQuiz(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      if (activeMode === "flashcards") {
        loadDeck(selectedDocId);
      } else {
        loadQuiz(selectedDocId);
      }
    }
  }, [selectedDocId, activeMode, loadDeck, loadQuiz]);

  const activeDoc = documents.find((d) => d.id === selectedDocId);
  const activeTitle = activeDoc?.metadata?.title || activeDoc?.filename || "Selected Research Paper";

  // Flashcard handlers
  const handleNextCard = () => {
    if (!deck || deck.cards.length === 0) return;
    setIsFlipped(false);
    setCurrentCardIndex((prev) => (prev + 1) % deck.cards.length);
  };

  const handlePrevCard = () => {
    if (!deck || deck.cards.length === 0) return;
    setIsFlipped(false);
    setCurrentCardIndex((prev) => (prev - 1 + deck.cards.length) % deck.cards.length);
  };

  const handleShuffle = () => {
    if (!deck || deck.cards.length === 0) return;
    setIsFlipped(false);
    const shuffled = [...deck.cards].sort(() => Math.random() - 0.5);
    setDeck({ ...deck, cards: shuffled });
    setCurrentCardIndex(0);
  };

  const handleExportAnki = async () => {
    if (!selectedDocId) return;
    setIsExportingAnki(true);
    try {
      const cleanName = (activeDoc?.filename || "paper").replace(/\.pdf$/i, "");
      await api.downloadFlashcardsAnki(selectedDocId, `anki_${cleanName}.csv`);
    } catch (err: any) {
      alert("Export failed: " + (err.message || "Could not download Anki CSV."));
    } finally {
      setIsExportingAnki(false);
    }
  };

  // Quiz handlers
  const handleSelectOption = (questionId: string, option: string) => {
    if (evaluation) return; // Prevent change after grading
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: option,
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!quiz) return;
    setIsSubmittingQuiz(true);
    try {
      const res = await api.evaluateQuiz(quiz.id, selectedAnswers);
      setEvaluation(res);
    } catch (err: any) {
      alert("Quiz submission failed: " + (err.message || "Could not grade quiz."));
    } finally {
      setIsSubmittingQuiz(false);
    }
  };

  const handleResetQuiz = () => {
    setEvaluation(null);
    setSelectedAnswers({});
  };

  const currentCard: Flashcard | undefined = deck?.cards[currentCardIndex];

  return (
    <div className="space-y-6">
      {/* Header & Mode Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#0E1424] border border-[#1E293B] p-5 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
              <GraduationCap className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-wide">
              Research Study & Productivity Suite
            </h1>
          </div>
          <p className="text-xs text-slate-400">
            Interactive conceptual flashcards, Anki spaced-repetition export, and diagnostic multiple-choice quizzes with strict provenance citations.
          </p>
        </div>

        {/* Mode Buttons */}
        <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-800 p-1 rounded-xl shrink-0">
          <button
            onClick={() => setActiveMode("flashcards")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeMode === "flashcards"
                ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Interactive Flashcards</span>
          </button>
          <button
            onClick={() => setActiveMode("quiz")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeMode === "quiz"
                ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            <span>Diagnostic Quiz</span>
          </button>
        </div>
      </div>

      {/* Target Document Selector */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#0A0E1A] border border-[#1E293B] p-4 rounded-xl">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="text-xs text-slate-400 shrink-0">Active Paper:</span>
          {completedDocs.length > 0 ? (
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500/60 max-w-md truncate"
            >
              {completedDocs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.metadata?.title || d.filename}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-xs text-amber-400">
              No parsed documents found in library. Please ingest a PDF first.
            </span>
          )}
        </div>

        {/* Regenerate Action */}
        {selectedDocId && (
          <button
            onClick={() =>
              activeMode === "flashcards"
                ? loadDeck(selectedDocId, true)
                : loadQuiz(selectedDocId, true)
            }
            disabled={isLoadingDeck || isLoadingQuiz}
            className="flex items-center justify-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-cyan-300 font-medium transition-colors"
          >
            <RotateCw
              className={`w-3.5 h-3.5 ${
                isLoadingDeck || isLoadingQuiz ? "animate-spin" : ""
              }`}
            />
            <span>Regenerate {activeMode === "flashcards" ? "Flashcards" : "Quiz"}</span>
          </button>
        )}
      </div>

      {/* Error state */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/50 flex items-center space-x-3 text-red-200 text-xs">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* MODE 1: FLASHCARDS */}
      {activeMode === "flashcards" && (
        <div className="space-y-6">
          {isLoadingDeck ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4 rounded-2xl bg-slate-900/40 border border-slate-800/80">
              <RotateCw className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-300 font-medium">
                Extracting grounded conceptual flashcards with page provenance...
              </p>
            </div>
          ) : deck && deck.cards.length > 0 ? (
            <div className="flex flex-col items-center space-y-6 max-w-3xl mx-auto">
              {/* Deck Info & Actions bar */}
              <div className="w-full flex items-center justify-between text-xs text-slate-400 px-1">
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 rounded-md bg-cyan-950/60 border border-cyan-800/40 text-cyan-300 font-mono font-medium">
                    Card {currentCardIndex + 1} of {deck.cards.length}
                  </span>
                  <span>•</span>
                  <span className="text-slate-400">
                    Section: <strong className="text-slate-200">{currentCard?.section_title || "General"}</strong>
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleShuffle}
                    title="Shuffle Cards"
                    className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-cyan-300 transition-colors"
                  >
                    <Shuffle className="w-4 h-4" />
                  </button>

                  <button
                    onClick={handleExportAnki}
                    disabled={isExportingAnki}
                    className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 font-medium transition-colors"
                  >
                    <Download className={`w-3.5 h-3.5 ${isExportingAnki ? "animate-bounce" : ""}`} />
                    <span>{isExportingAnki ? "Exporting..." : "Export to Anki (.CSV)"}</span>
                  </button>
                </div>
              </div>

              {/* 3D Flip Card Container */}
              <div
                onClick={() => setIsFlipped(!isFlipped)}
                className="w-full min-h-[340px] cursor-pointer perspective-[1000px] select-none"
              >
                <div
                  className={`relative w-full h-full min-h-[340px] rounded-3xl transition-transform duration-500 transform-style-3d ${
                    isFlipped ? "rotate-y-180" : ""
                  }`}
                  style={{
                    transformStyle: "preserve-3d",
                    transform: isFlipped ? "rotateY(180deg)" : "rotateY(0deg)",
                  }}
                >
                  {/* FRONT FACE (Concept) */}
                  <div
                    className="absolute inset-0 w-full h-full rounded-3xl bg-gradient-to-br from-[#111A2E] via-[#0E1526] to-[#0A0E1A] border-2 border-cyan-500/30 p-8 flex flex-col justify-between shadow-2xl backface-hidden"
                    style={{ backfaceVisibility: "hidden" }}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono text-[11px]">
                        <Sparkles className="w-3 h-3 text-cyan-400" />
                        <span>Core Concept</span>
                      </span>
                      <span className="text-slate-500 font-mono text-[11px]">
                        Page {currentCard?.page_number || 1}
                      </span>
                    </div>

                    <div className="text-center py-6">
                      <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
                        {currentCard?.front_concept}
                      </h2>
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/60 pt-4">
                      <span className="text-[11px] text-slate-400">
                        Section: {currentCard?.section_title}
                      </span>
                      <span className="text-cyan-400 font-medium text-xs flex items-center space-x-1 animate-pulse">
                        <span>Click to reveal definition</span>
                        <RotateCw className="w-3 h-3" />
                      </span>
                    </div>
                  </div>

                  {/* BACK FACE (Definition & Provenance) */}
                  <div
                    className="absolute inset-0 w-full h-full rounded-3xl bg-gradient-to-br from-[#0B1528] via-[#0E1C33] to-[#0A1020] border-2 border-blue-500/40 p-8 flex flex-col justify-between shadow-2xl backface-hidden"
                    style={{
                      backfaceVisibility: "hidden",
                      transform: "rotateY(180deg)",
                    }}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-blue-950/80 text-blue-300 border border-blue-800/60 font-mono text-[11px]">
                        <CheckCircle2 className="w-3 h-3 text-blue-400" />
                        <span>Scientific Definition</span>
                      </span>
                      <span className="text-slate-400 font-mono text-[11px]">
                        {currentCard?.source_citation}
                      </span>
                    </div>

                    <div className="space-y-4 my-auto py-2">
                      <p className="text-base sm:text-lg text-slate-100 leading-relaxed font-normal">
                        {currentCard?.back_definition}
                      </p>

                      {currentCard?.source_excerpt && (
                        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 italic">
                          "{currentCard.source_excerpt}"
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/60 pt-4">
                      <span className="text-xs text-cyan-300 font-mono">
                        Provenance Verified • Page {currentCard?.page_number || 1}
                      </span>
                      <span className="text-slate-400 text-xs flex items-center space-x-1">
                        <span>Click to flip back</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Navigation Controls */}
              <div className="flex items-center space-x-4">
                <button
                  onClick={handlePrevCard}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold transition-all active:scale-95 shadow-sm"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Previous</span>
                </button>

                <button
                  onClick={() => setIsFlipped(!isFlipped)}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-bold transition-all active:scale-95 shadow-md shadow-cyan-500/20"
                >
                  Flip Card (Space)
                </button>

                <button
                  onClick={handleNextCard}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold transition-all active:scale-95 shadow-sm"
                >
                  <span>Next</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-20 rounded-2xl bg-slate-900/30 border border-slate-800/60 space-y-3">
              <BookOpen className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-sm text-slate-400">
                No flashcards generated yet for this paper.
              </p>
              <button
                onClick={() => loadDeck(selectedDocId, true)}
                className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs"
              >
                Generate Study Cards
              </button>
            </div>
          )}
        </div>
      )}

      {/* MODE 2: DIAGNOSTIC QUIZ */}
      {activeMode === "quiz" && (
        <div className="space-y-6">
          {isLoadingQuiz ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4 rounded-2xl bg-slate-900/40 border border-slate-800/80">
              <RotateCw className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-300 font-medium">
                Generating 5 diagnostic multiple-choice questions with answer keys...
              </p>
            </div>
          ) : quiz && quiz.questions.length > 0 ? (
            <div className="space-y-6 max-w-4xl mx-auto">
              {/* Score Evaluation Banner if completed */}
              {evaluation && (
                <div className="p-6 rounded-2xl bg-gradient-to-r from-[#0C1B33] via-[#0E2347] to-[#0A172D] border border-cyan-500/40 shadow-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 rounded-xl bg-cyan-500/20 border border-cyan-400/30 flex items-center justify-center text-cyan-300">
                        <Award className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-white">
                          Quiz Evaluation Complete
                        </h3>
                        <p className="text-xs text-slate-300">
                          Diagnostic evaluation grounded in "{activeTitle}".
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-3xl font-extrabold text-cyan-400 font-mono">
                        {evaluation.score} / {evaluation.total_questions}
                      </span>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {evaluation.percentage}% Score
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
                    <span className="text-slate-400">
                      Performance:{" "}
                      <strong className={evaluation.percentage >= 80 ? "text-emerald-400" : evaluation.percentage >= 60 ? "text-amber-400" : "text-rose-400"}>
                        {evaluation.percentage >= 80 ? "Mastery Achieved" : evaluation.percentage >= 60 ? "Solid Comprehension" : "Review Recommended"}
                      </strong>
                    </span>

                    <button
                      onClick={handleResetQuiz}
                      className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold transition-colors"
                    >
                      Retake Quiz
                    </button>
                  </div>
                </div>
              )}

              {/* Questions List */}
              <div className="space-y-6">
                {quiz.questions.map((q, idx) => {
                  const evalResult = evaluation?.results.find(
                    (r) => r.question_id === q.question_id
                  );
                  const selected = selectedAnswers[q.question_id];

                  return (
                    <div
                      key={q.question_id || idx}
                      className={`p-6 rounded-2xl bg-[#0E1424] border transition-all ${
                        evalResult
                          ? evalResult.is_correct
                            ? "border-emerald-500/40 bg-emerald-950/10"
                            : "border-red-500/40 bg-red-950/10"
                          : "border-[#1E293B]"
                      }`}
                    >
                      {/* Question header */}
                      <div className="flex items-start justify-between gap-3 mb-4">
                        <div className="space-y-1">
                          <span className="text-[11px] font-mono text-cyan-400 font-semibold uppercase tracking-wider">
                            Question {idx + 1} of {quiz.questions.length}
                          </span>
                          <h4 className="text-base font-semibold text-white leading-relaxed">
                            {q.question_text}
                          </h4>
                        </div>

                        {evalResult && (
                          <div className="shrink-0">
                            {evalResult.is_correct ? (
                              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-xs font-semibold">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Correct</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-red-950/80 border border-red-800 text-red-400 text-xs font-semibold">
                                <XCircle className="w-3.5 h-3.5" />
                                <span>Incorrect</span>
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Options Radio List */}
                      <div className="space-y-2.5">
                        {q.options.map((opt, optIdx) => {
                          const isOptionSelected = selected === opt;
                          const isOptionCorrect = evalResult && opt === evalResult.correct_answer;
                          const isOptionWrongSelected =
                            evalResult && isOptionSelected && !evalResult.is_correct;

                          let optionStyles = "bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-900 hover:border-slate-700";

                          if (evalResult) {
                            if (isOptionCorrect) {
                              optionStyles = "bg-emerald-950/40 border-emerald-500 text-emerald-200 font-semibold";
                            } else if (isOptionWrongSelected) {
                              optionStyles = "bg-red-950/40 border-red-500 text-red-200";
                            } else {
                              optionStyles = "bg-slate-900/30 border-slate-900/60 text-slate-500";
                            }
                          } else if (isOptionSelected) {
                            optionStyles = "bg-cyan-950/70 border-cyan-500 text-cyan-200 font-semibold shadow-sm";
                          }

                          return (
                            <div
                              key={optIdx}
                              onClick={() => handleSelectOption(q.question_id, opt)}
                              className={`p-3.5 rounded-xl border text-xs flex items-center space-x-3 cursor-pointer transition-all ${optionStyles}`}
                            >
                              <div
                                className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 text-[10px] font-mono font-bold ${
                                  isOptionCorrect
                                    ? "bg-emerald-500 border-emerald-400 text-slate-950"
                                    : isOptionWrongSelected
                                    ? "bg-red-500 border-red-400 text-white"
                                    : isOptionSelected
                                    ? "bg-cyan-500 border-cyan-400 text-slate-950"
                                    : "border-slate-700 text-slate-400"
                                }`}
                              >
                                {String.fromCharCode(65 + optIdx)}
                              </div>
                              <span className="flex-1 leading-normal">{opt}</span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Post-evaluation Explanation & Provenance */}
                      {evalResult && (
                        <div className="mt-4 p-4 rounded-xl bg-[#0A0E1A] border border-slate-800/80 space-y-2 text-xs">
                          <div className="flex items-center space-x-2 text-cyan-400 font-semibold text-[11px] uppercase tracking-wide">
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Scientific Explanation & Provenance</span>
                          </div>
                          <p className="text-slate-300 leading-relaxed font-normal">
                            {evalResult.explanation}
                          </p>
                          <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-slate-400 text-[11px] font-mono">
                            <span>Citation: {evalResult.source_citation}</span>
                            <span>Verified Page: {evalResult.page_number || 1}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Submit Quiz Actions */}
              {!evaluation && (
                <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-xs text-slate-400">
                    Answered: <strong className="text-slate-200">{Object.keys(selectedAnswers).length}</strong> of {quiz.questions.length} questions
                  </span>

                  <button
                    onClick={handleSubmitQuiz}
                    disabled={isSubmittingQuiz || Object.keys(selectedAnswers).length === 0}
                    className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs shadow-md shadow-cyan-500/20 transition-all active:scale-95 disabled:opacity-50"
                  >
                    <span>{isSubmittingQuiz ? "Grading..." : "Submit Answers & Evaluate"}</span>
                    <CheckCircle2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-20 rounded-2xl bg-slate-900/30 border border-slate-800/60 space-y-3">
              <HelpCircle className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-sm text-slate-400">
                No diagnostic quiz generated yet for this paper.
              </p>
              <button
                onClick={() => loadQuiz(selectedDocId, true)}
                className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs"
              >
                Generate Diagnostic Quiz
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
