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
  RotateCcw,
  Award,
} from "lucide-react";
import { DocumentItem, FlashcardDeck, Flashcard, Quiz, QuizEvaluationResult } from "../types";
import { api } from "../lib/api";

interface AdaptiveStudySuiteProps {
  documents: DocumentItem[];
  initialDocumentId?: string | null;
}

export const AdaptiveStudySuite: React.FC<AdaptiveStudySuiteProps> = ({
  documents,
  initialDocumentId,
}) => {
  const completedDocs = documents.filter((d) => d.status === "COMPLETED");
  const fallbackDocId = completedDocs[0]?.id || documents[0]?.id || "";
  const [selectedDocId, setSelectedDocId] = useState<string>(
    initialDocumentId || fallbackDocId
  );

  // Sync selectedDocId whenever initialDocumentId or documents change
  useEffect(() => {
    if (initialDocumentId) {
      setSelectedDocId(initialDocumentId);
    } else if (!selectedDocId && fallbackDocId) {
      setSelectedDocId(fallbackDocId);
    }
  }, [initialDocumentId, fallbackDocId]);

  const [activeMode, setActiveMode] = useState<"flashcards" | "quiz">("flashcards");

  // Flashcards state
  const [deck, setDeck] = useState<FlashcardDeck | null>(null);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isLoadingDeck, setIsLoadingDeck] = useState(false);
  const [isExportingAnki, setIsExportingAnki] = useState(false);

  // Self-assessment tracking state
  const [knownCards, setKnownCards] = useState<Record<string, boolean>>({});

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
      let data: FlashcardDeck;
      if (forceGenerate) {
        data = await api.generateFlashcards(docId);
      } else {
        data = await api.getFlashcards(docId);
      }
      setDeck(data);
      setCurrentCardIndex(0);
      setIsFlipped(false);
    } catch (err: any) {
      console.error("Failed to load flashcard deck:", err);
      setErrorMsg("Failed to generate flashcards. Make sure the document is fully indexed.");
    } finally {
      setIsLoadingDeck(false);
    }
  }, []);

  // Load Quiz
  const loadQuiz = useCallback(async (docId: string, forceGenerate = false) => {
    if (!docId) return;
    setIsLoadingQuiz(true);
    setErrorMsg(null);
    try {
      let q: Quiz;
      if (forceGenerate) {
        q = await api.generateQuiz(docId);
      } else {
        q = await api.getQuiz(docId);
      }
      setQuiz(q);
      setSelectedAnswers({});
      setEvaluation(null);
    } catch (err: any) {
      console.error("Failed to load quiz:", err);
      setErrorMsg("Failed to generate quiz questions.");
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

  const handleCardFeedback = (knewIt: boolean) => {
    if (!deck || !deck.cards[currentCardIndex]) return;
    const cardId = deck.cards[currentCardIndex].id;
    setKnownCards((prev) => ({ ...prev, [cardId]: knewIt }));
    
    // Auto-advance to next card
    if (currentCardIndex < deck.cards.length - 1) {
      setCurrentCardIndex((i) => i + 1);
      setIsFlipped(false);
    }
  };

  const handleExportAnki = async () => {
    if (!selectedDocId) return;
    setIsExportingAnki(true);
    try {
      await api.downloadFlashcardsAnki(selectedDocId, `veritas_deck_${selectedDocId.slice(0, 8)}.csv`);
    } catch (err: any) {
      alert(`Anki export failed: ${err.message}`);
    } finally {
      setIsExportingAnki(false);
    }
  };

  const handleAnswerSelect = (questionId: string, optionKey: string) => {
    if (evaluation) return;
    setSelectedAnswers((prev) => ({ ...prev, [questionId]: optionKey }));
  };

  const handleSubmitQuiz = async () => {
    if (!quiz) return;
    setIsSubmittingQuiz(true);
    try {
      const result = await api.evaluateQuiz(quiz.id, selectedAnswers);
      setEvaluation(result);
    } catch (err: any) {
      alert(`Quiz submission failed: ${err.message}`);
    } finally {
      setIsSubmittingQuiz(false);
    }
  };

  const currentCard = deck?.cards[currentCardIndex];

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full">
      {/* Header Bar */}
      <div className="bg-panel border border-border rounded-2xl p-5 shadow-subtle flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <GraduationCap className="w-5 h-5 text-veritas-600" />
            <h1 className="text-lg font-bold text-ink-900">Adaptive Study Suite</h1>
          </div>
          <p className="text-xs text-ink-500 mt-0.5">
            Grounded active-recall flashcards and automated multiple-choice self-assessments.
          </p>
        </div>

        {/* Controls: Target Paper & Study Mode */}
        <div className="flex items-center space-x-2 w-full md:w-auto">
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="text-xs bg-surface-subtle border border-border rounded-xl px-3 py-2 text-ink-900 focus:outline-none focus:border-veritas-500 max-w-[200px] truncate"
          >
            {completedDocs.length === 0 && <option value="">No indexed papers</option>}
            {completedDocs.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
          </select>

          <div className="flex items-center space-x-1 bg-surface-subtle p-1 rounded-xl border border-border text-xs">
            <button
              onClick={() => setActiveMode("flashcards")}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                activeMode === "flashcards"
                  ? "bg-panel text-ink-900 shadow-subtle font-semibold"
                  : "text-ink-500 hover:text-ink-900"
              }`}
            >
              Flashcards
            </button>
            <button
              onClick={() => setActiveMode("quiz")}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                activeMode === "quiz"
                  ? "bg-panel text-ink-900 shadow-subtle font-semibold"
                  : "text-ink-500 hover:text-ink-900"
              }`}
            >
              Quiz Assessment
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* FLASHCARD INTERFACE */}
      {activeMode === "flashcards" ? (
        <div className="space-y-6">
          {isLoadingDeck ? (
            <div className="bg-panel border border-border rounded-2xl p-16 text-center text-xs text-ink-400 space-y-3 shadow-subtle">
              <RotateCw className="w-6 h-6 animate-spin text-veritas-600 mx-auto" />
              <p>Synthesizing flashcards with exact page provenance...</p>
            </div>
          ) : !deck || deck.cards.length === 0 ? (
            <div className="bg-panel border border-border rounded-2xl p-12 text-center space-y-3 shadow-subtle">
              <BookOpen className="w-8 h-8 text-ink-300 mx-auto" />
              <h3 className="text-sm font-semibold text-ink-900">No Flashcard Deck Generated Yet</h3>
              <p className="text-xs text-ink-500">Generate 10-15 atomic conceptual cards for this research paper.</p>
              <button
                onClick={() => loadDeck(selectedDocId, true)}
                className="bg-ink-900 hover:bg-ink-700 text-white text-xs font-medium px-4 py-2 rounded-xl transition-colors shadow-subtle"
              >
                Generate Flashcards Now
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Card Meta & Controls */}
              <div className="flex items-center justify-between text-xs text-ink-500 px-2">
                <span>
                  Card <strong className="text-ink-900">{currentCardIndex + 1}</strong> of {deck.cards.length}
                </span>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => loadDeck(selectedDocId, true)}
                    className="p-1.5 hover:bg-surface-subtle border border-border rounded-lg text-ink-500"
                    title="Regenerate Deck"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={handleExportAnki}
                    disabled={isExportingAnki}
                    className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-surface-subtle hover:bg-surface-hover text-ink-700 border border-border rounded-lg"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export Anki (.apkg)</span>
                  </button>
                </div>
              </div>

              {/* 3D Flip Card Element */}
              <div
                onClick={() => setIsFlipped(!isFlipped)}
                className="min-h-[280px] bg-panel border border-border hover:border-veritas-300 rounded-3xl p-8 sm:p-12 shadow-card cursor-pointer flex flex-col justify-between transition-all select-none group"
              >
                <div className="flex items-center justify-between text-xs text-ink-400">
                  <span className="font-mono text-[10px] uppercase tracking-wider bg-surface-subtle px-2 py-0.5 rounded border border-border">
                    {isFlipped ? "Answer / Explanation" : "Prompt / Concept"}
                  </span>
                  <span className="text-[11px] group-hover:text-veritas-600 transition-colors">
                    Click anywhere to flip ↷
                  </span>
                </div>

                <div className="my-6">
                  {isFlipped ? (
                    <div className="space-y-4 animate-fadeIn">
                      <p className="text-sm sm:text-base text-ink-900 leading-relaxed font-sans">
                        {currentCard?.back_definition}
                      </p>
                      {currentCard?.source_citation && (
                        <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-50 text-amber-800 border border-amber-200 text-xs font-mono">
                          <span>{currentCard.source_citation}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <h2 className="text-lg sm:text-xl font-bold text-ink-900 leading-snug">
                      {currentCard?.front_concept}
                    </h2>
                  )}
                </div>

                <div className="text-[11px] text-ink-400 text-right">
                  {isFlipped ? "Provenanced Grounding" : "Active Recall Trigger"}
                </div>
              </div>

              {/* Navigation & Recall Buttons */}
              <div className="flex items-center justify-between gap-4 pt-2">
                <button
                  onClick={() => {
                    setCurrentCardIndex((i) => Math.max(0, i - 1));
                    setIsFlipped(false);
                  }}
                  disabled={currentCardIndex === 0}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-xl border border-border hover:bg-surface-subtle disabled:opacity-30 text-xs font-medium text-ink-700"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Previous</span>
                </button>

                {/* Self-Assessment Triggers */}
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleCardFeedback(false)}
                    className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-medium transition-colors"
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Review Again</span>
                  </button>

                  <button
                    onClick={() => handleCardFeedback(true)}
                    className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 text-xs font-medium transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Mastered</span>
                  </button>
                </div>

                <button
                  onClick={() => {
                    setCurrentCardIndex((i) => Math.min(deck.cards.length - 1, i + 1));
                    setIsFlipped(false);
                  }}
                  disabled={currentCardIndex === deck.cards.length - 1}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-xl border border-border hover:bg-surface-subtle disabled:opacity-30 text-xs font-medium text-ink-700"
                >
                  <span>Next</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* QUIZ ASSESSMENT INTERFACE */
        <div className="space-y-6">
          {isLoadingQuiz ? (
            <div className="bg-panel border border-border rounded-2xl p-16 text-center text-xs text-ink-400 space-y-3 shadow-subtle">
              <RotateCw className="w-6 h-6 animate-spin text-veritas-600 mx-auto" />
              <p>Generating multiple-choice evaluation quiz...</p>
            </div>
          ) : !quiz || quiz.questions.length === 0 ? (
            <div className="bg-panel border border-border rounded-2xl p-12 text-center space-y-3 shadow-subtle">
              <Award className="w-8 h-8 text-ink-300 mx-auto" />
              <h3 className="text-sm font-semibold text-ink-900">No Assessment Quiz Ready</h3>
              <p className="text-xs text-ink-500">Test your mastery of this paper with auto-evaluated questions.</p>
              <button
                onClick={() => loadQuiz(selectedDocId, true)}
                className="bg-ink-900 hover:bg-ink-700 text-white text-xs font-medium px-4 py-2 rounded-xl transition-colors shadow-subtle"
              >
                Generate Assessment Quiz
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Questions List */}
              <div className="space-y-4">
                {quiz.questions.map((q, idx) => {
                  const evalItem = evaluation?.results?.find((r) => r.question_id === q.question_id);
                  return (
                    <div key={q.question_id} className="bg-panel border border-border rounded-2xl p-6 shadow-subtle space-y-4">
                      <div className="flex items-start justify-between">
                        <span className="text-xs font-mono font-semibold text-ink-400">Question {idx + 1}</span>
                        {evalItem && (
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center space-x-1 ${
                              evalItem.is_correct
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {evalItem.is_correct ? "Correct (+1)" : "Incorrect"}
                          </span>
                        )}
                      </div>

                      <p className="text-sm font-semibold text-ink-900">{q.question_text}</p>

                      {/* Options Grid */}
                      <div className="space-y-2">
                        {q.options.map((optText, optIdx) => {
                          const key = String.fromCharCode(65 + optIdx); // 'A', 'B', 'C', 'D'
                          const isSelected = selectedAnswers[q.question_id] === optText || selectedAnswers[q.question_id] === key;
                          return (
                            <button
                              key={optIdx}
                              disabled={Boolean(evaluation)}
                              onClick={() => handleAnswerSelect(q.question_id, optText)}
                              className={`w-full text-left p-3 rounded-xl border text-xs transition-colors flex items-center space-x-3 ${
                                isSelected
                                  ? "bg-veritas-50 text-veritas-700 border-veritas-300 font-medium"
                                  : "border-border hover:bg-surface-subtle text-ink-700"
                              }`}
                            >
                              <span className="w-5 h-5 rounded-full border border-border flex items-center justify-center font-bold text-[11px] uppercase shrink-0">
                                {key}
                              </span>
                              <span>{optText}</span>
                            </button>
                          );
                        })}
                      </div>

                      {evalItem && evalItem.explanation && (
                        <div className="p-3 bg-surface-subtle rounded-xl border border-border text-xs text-ink-500 space-y-1">
                          <span className="font-semibold text-ink-900">Explanation & Citation:</span>
                          <p>{evalItem.explanation}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Submit / Score Bar */}
              <div className="bg-panel border border-border rounded-2xl p-5 shadow-subtle flex items-center justify-between">
                <div>
                  {evaluation ? (
                    <div className="flex items-center space-x-2">
                      <Award className="w-5 h-5 text-veritas-gold" />
                      <span className="text-sm font-bold text-ink-900">
                        Score: {evaluation.percentage}% ({evaluation.score}/{evaluation.total_questions})
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs text-ink-500">
                      {Object.keys(selectedAnswers).length} of {quiz.questions.length} answered
                    </span>
                  )}
                </div>

                {!evaluation ? (
                  <button
                    onClick={handleSubmitQuiz}
                    disabled={isSubmittingQuiz || Object.keys(selectedAnswers).length === 0}
                    className="bg-ink-900 hover:bg-ink-700 disabled:opacity-50 text-white px-5 py-2 rounded-xl text-xs font-semibold shadow-subtle transition-colors"
                  >
                    {isSubmittingQuiz ? "Evaluating..." : "Submit Answers"}
                  </button>
                ) : (
                  <button
                    onClick={() => loadQuiz(selectedDocId, true)}
                    className="bg-veritas-50 text-veritas-700 border border-veritas-200 px-4 py-2 rounded-xl text-xs font-semibold hover:bg-veritas-100 transition-colors"
                  >
                    Retake / New Questions
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
