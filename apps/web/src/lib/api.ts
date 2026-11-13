import {
  DocumentItem,
  DocumentDetail,
  DocumentUploadResponse,
  DocumentProcessingJob,
  User,
  ChatSession,
  ChatSessionDetail,
  ChatMessage,
  PaperSynthesis,
  LiteratureMatrix,
  DiscoverySearchResponse,
  DirectIngestResponse,
  CitationNetworkResponse,
  WorkspaceGraph,
  AgentEvent,
  FlashcardDeck,
  Quiz,
  QuizEvaluationResult,
  WorkspaceItem,
  WorkspaceDetail,
  WorkspaceMember,
  IntegrationStatus,
  WebhookSubscriptionItem,
  ZoteroSyncSummary,
  WorkspaceUsageSummary,
  WorkspaceActivity,
  DocumentAuditResponse,
  SecurityIncidentResponse,
} from "../types";

const PRODUCTION_RENDER_API = "https://veritas-backend-3cge.onrender.com/api/v1";
const LOCAL_DEV_API = "http://127.0.0.1:8000/api/v1";

/**
 * Hardcoded absolute API Base URL resolution.
 * If hostname is not localhost or 127.0.0.1, it unconditionally returns the Render backend URL.
 */
function getApiBaseUrl(): string {
  if (typeof window !== "undefined" && window.location) {
    const { hostname } = window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return LOCAL_DEV_API;
    }
    return PRODUCTION_RENDER_API;
  }
  return PRODUCTION_RENDER_API;
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("veritas_auth_token");
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("veritas_auth_token", token);
      } else {
        localStorage.removeItem("veritas_auth_token");
      }
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== "undefined") {
      this.token = localStorage.getItem("veritas_auth_token");
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const baseUrl = getApiBaseUrl();
    const res = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 204) {
      return {} as T;
    }

    if (!res.ok) {
      let errDetail = "An unexpected error occurred.";
      try {
        const errorJson = await res.json();
        errDetail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        errDetail = res.statusText || `HTTP ${res.status}`;
      }
      throw new Error(errDetail);
    }

    return res.json() as Promise<T>;
  }

  // Auth Endpoints
  async register(email: string, password: string, fullName?: string): Promise<{ access_token: string; user: User }> {
    const data = await this.request<{ access_token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const data = await this.request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<User> {
    return this.request<User>("/auth/me");
  }

  logout() {
    this.setToken(null);
  }

  // Document Endpoints
  async uploadDocument(
    file: File,
    onProgress?: (pct: number) => void
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const token = this.getToken();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${getApiBaseUrl()}/documents/upload`);
      if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      }

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const json = JSON.parse(xhr.responseText);
            resolve(json);
          } catch (err) {
            reject(new Error("Invalid JSON response from server"));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || `HTTP ${xhr.status}`));
          } catch {
            reject(new Error(xhr.statusText || `Upload failed with status ${xhr.status}`));
          }
        }
      };

      xhr.onerror = () => reject(new Error("Network error during file upload"));
      xhr.send(formData);
    });
  }

  async uploadBatch(files: File[]): Promise<{ successful: any[]; failed: any[]; total_uploaded: number }> {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    return this.request("/documents/upload-batch", {
      method: "POST",
      body: formData,
    });
  }

  async listDocuments(workspaceId?: string, status?: string): Promise<DocumentItem[]> {
    const params = new URLSearchParams();
    if (workspaceId) params.append("workspace_id", workspaceId);
    if (status) params.append("status", status);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    return this.request<DocumentItem[]>(`/documents${queryString}`);
  }

  async getDocumentDetail(id: string): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/documents/${id}`);
  }

  async getProcessingStatus(id: string): Promise<DocumentProcessingJob> {
    return this.request<DocumentProcessingJob>(`/documents/${id}/status`);
  }

  async retryProcessing(id: string): Promise<DocumentProcessingJob> {
    return this.request<DocumentProcessingJob>(`/documents/${id}/retry`, {
      method: "POST",
    });
  }

  async deleteDocument(id: string): Promise<void> {
    return this.request<void>(`/documents/${id}`, {
      method: "DELETE",
    });
  }

  getDownloadUrl(id: string): string {
    return `${getApiBaseUrl()}/documents/${id}/download`;
  }

  // Phase 2: Hybrid Retrieval Endpoint
  async searchHybrid(
    query: string,
    documentId?: string,
    topK: number = 10
  ): Promise<{ query: string; tenant_id: string; total_results: number; results: any[] }> {
    return this.request("/retrieval/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        document_id: documentId || null,
        top_k: topK,
      }),
    });
  }

  // Phase 3: Grounded AI Assistant & Chat Endpoints
  async createChatSession(title?: string, documentId?: string): Promise<ChatSession> {
    return this.request<ChatSession>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({
        title: title || "New Research Session",
        document_id: documentId || null,
      }),
    });
  }

  async listChatSessions(): Promise<ChatSession[]> {
    return this.request<ChatSession[]>("/chat/sessions");
  }

  async getChatSession(sessionId: string): Promise<ChatSessionDetail> {
    return this.request<ChatSessionDetail>(`/chat/sessions/${sessionId}`);
  }

  async deleteChatSession(sessionId: string): Promise<void> {
    return this.request<void>(`/chat/sessions/${sessionId}`, {
      method: "DELETE",
    });
  }

  async sendChatMessage(sessionId: string, content: string): Promise<ChatMessage> {
    return this.request<ChatMessage>(`/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  }

  // Phase 5: Scientific Intelligence & Literature Analysis
  async getPaperSynthesis(documentId: string): Promise<PaperSynthesis> {
    return this.request<PaperSynthesis>(`/analysis/summary/${documentId}`);
  }

  async generateLiteratureMatrix(documentIds: string[], topicQuery?: string): Promise<LiteratureMatrix> {
    return this.request<LiteratureMatrix>("/analysis/matrix", {
      method: "POST",
      body: JSON.stringify({
        document_ids: documentIds,
        topic_query: topicQuery || null,
      }),
    });
  }

  // Phase 6: Academic Research Discovery
  async searchGlobalLiterature(
    query: string,
    page = 1,
    perPage = 10,
    author?: string,
    year?: number
  ): Promise<DiscoverySearchResponse> {
    const params = new URLSearchParams({
      query,
      page: page.toString(),
      per_page: perPage.toString(),
    });
    if (author) params.append("author", author);
    if (year) params.append("year", year.toString());
    return this.request<DiscoverySearchResponse>(`/discovery/search?${params.toString()}`);
  }

  async ingestPaperFromExternal(
    doiOrUrl: string,
    workspaceId?: string,
    title?: string
  ): Promise<DirectIngestResponse> {
    return this.request<DirectIngestResponse>("/discovery/ingest", {
      method: "POST",
      body: JSON.stringify({
        doi_or_url: doiOrUrl,
        workspace_id: workspaceId || null,
        title: title || null,
      }),
    });
  }

  async getCitationNetwork(documentId: string): Promise<CitationNetworkResponse> {
    return this.request<CitationNetworkResponse>(`/discovery/citations/${documentId}`);
  }

  // Phase 8: Research Knowledge Graph
  async getWorkspaceKnowledgeGraph(): Promise<WorkspaceGraph> {
    return this.request<WorkspaceGraph>("/graph/workspace");
  }

  async extractDocumentGraph(documentId: string): Promise<{
    status: string;
    document_id: string;
    nodes_extracted: number;
    edges_extracted: number;
  }> {
    return this.request(`/graph/extract/${documentId}`, {
      method: "POST",
    });
  }

  // Phase 9: AI Research Agent (SSE Stream)
  async runAgentTaskStream(
    objective: string,
    onEvent: (event: AgentEvent) => void,
    maxIterations = 5
  ): Promise<void> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${getApiBaseUrl()}/agent/task`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        objective,
        max_iterations: maxIterations,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Agent request failed" }));
      throw new Error(err.detail || "Agent request failed");
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("ReadableStream not supported by browser");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          try {
            const data: AgentEvent = JSON.parse(trimmed.slice(6));
            onEvent(data);
          } catch (e) {
            console.error("Failed to parse SSE event chunk", e);
          }
        }
      }
    }
  }

  // Phase 10: Learning & Research Productivity
  async getFlashcards(documentId: string): Promise<FlashcardDeck> {
    try {
      const deck = await this.request<FlashcardDeck>(`/learning/flashcards/${documentId}`);
      if (deck.status === "not_generated") {
        return { ...deck, cards: [] };
      }
      if (!deck.cards && (deck as any).flashcards) {
        deck.cards = (deck as any).flashcards;
      }
      return deck;
    } catch (err: any) {
      // Gracefully catch 404/not-found to display the ungenerated study state
      if (err?.message?.includes("404") || err?.message?.includes("Not Found")) {
        return {
          id: `empty_${documentId}`,
          tenant_id: "",
          document_id: documentId,
          title: "Flashcard Deck Not Generated",
          card_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          cards: [],
          flashcards: [],
          status: "not_generated",
        };
      }
      throw err;
    }
  }

  async generateFlashcards(documentId: string): Promise<FlashcardDeck> {
    const deck = await this.request<FlashcardDeck>(`/learning/flashcards/generate/${documentId}`, {
      method: "POST",
    });
    if (!deck.cards && (deck as any).flashcards) {
      deck.cards = (deck as any).flashcards;
    }
    return deck;
  }

  async getQuiz(documentId: string): Promise<Quiz> {
    try {
      const q = await this.request<Quiz>(`/learning/quiz/${documentId}`);
      if (q.status === "not_generated") {
        return { ...q, questions: [] };
      }
      return q;
    } catch (err: any) {
      // Gracefully catch 404/not-found to display the ungenerated quiz state
      if (err?.message?.includes("404") || err?.message?.includes("Not Found")) {
        return {
          id: `empty_${documentId}`,
          tenant_id: "",
          document_id: documentId,
          title: "Diagnostic Quiz Not Generated",
          total_questions: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          questions: [],
          status: "not_generated",
        };
      }
      throw err;
    }
  }

  async generateQuiz(documentId: string): Promise<Quiz> {
    return this.request<Quiz>(`/learning/quiz/generate/${documentId}`, {
      method: "POST",
    });
  }

  async evaluateQuiz(quizId: string, answers: Record<string, string>): Promise<QuizEvaluationResult> {
    return this.request<QuizEvaluationResult>(`/learning/quiz/${quizId}/evaluate`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    });
  }

  async downloadFlashcardsAnki(documentId: string, filename = "anki_deck.csv"): Promise<void> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${getApiBaseUrl()}/learning/flashcards/${documentId}/export`, {
      headers,
    });

    if (!response.ok) {
      throw new Error("Failed to export Anki flashcards");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // Phase 11: Workspaces & Multi-User Collaboration
  async listWorkspaces(): Promise<WorkspaceItem[]> {
    return this.request<WorkspaceItem[]>("/workspaces");
  }

  async createWorkspace(name: string): Promise<WorkspaceItem> {
    return this.request<WorkspaceItem>("/workspaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  async getWorkspace(workspaceId: string): Promise<WorkspaceDetail> {
    return this.request<WorkspaceDetail>(`/workspaces/${workspaceId}`);
  }

  async inviteWorkspaceMember(workspaceId: string, email: string, role = "VIEWER"): Promise<WorkspaceMember> {
    return this.request<WorkspaceMember>(`/workspaces/${workspaceId}/members`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    });
  }

  async removeWorkspaceMember(workspaceId: string, userId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/workspaces/${workspaceId}/members/${userId}`, {
      method: "DELETE",
    });
  }

  // Phase 11: PDF Dossier Export
  async downloadDossierPdf(documentId: string, filename?: string): Promise<void> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${getApiBaseUrl()}/export/dossier/${documentId}`, {
      headers,
    });

    if (!response.ok) {
      throw new Error("Failed to export research dossier PDF");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `VERITAS_Dossier_${documentId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async getDocumentTree(documentId?: string): Promise<{ nodes: any[]; links: any[] }> {
    const q = documentId ? `?document_id=${encodeURIComponent(documentId)}` : "";
    return this.request<{ nodes: any[]; links: any[] }>(`/document/tree${q}`);
  }

  // Phase 12: Reference Managers & Advanced Integrations
  async connectZotero(apiKey: string, userId: string, workspaceId?: string): Promise<IntegrationStatus> {
    return this.request<IntegrationStatus>("/integrations/zotero/connect", {
      method: "POST",
      body: JSON.stringify({
        api_key: apiKey,
        user_id: userId,
        workspace_id: workspaceId || null,
      }),
    });
  }

  async syncZotero(workspaceId: string, limit = 50): Promise<ZoteroSyncSummary> {
    return this.request<ZoteroSyncSummary>("/integrations/zotero/sync", {
      method: "POST",
      body: JSON.stringify({ workspace_id: workspaceId, limit }),
    });
  }

  async getIntegrationStatus(workspaceId?: string): Promise<IntegrationStatus[]> {
    const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
    return this.request<IntegrationStatus[]>(`/integrations/status${query}`);
  }

  // Phase 12: Webhooks API
  async createWebhook(
    workspaceId: string,
    url: string,
    eventsSubscribed: string[],
    description?: string,
  ): Promise<WebhookSubscriptionItem> {
    return this.request<WebhookSubscriptionItem>("/webhooks", {
      method: "POST",
      body: JSON.stringify({
        workspace_id: workspaceId,
        url,
        events_subscribed: eventsSubscribed,
        description: description || null,
      }),
    });
  }

  async listWebhooks(workspaceId: string): Promise<WebhookSubscriptionItem[]> {
    return this.request<WebhookSubscriptionItem[]>(`/webhooks?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  async deleteWebhook(webhookId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/webhooks/${webhookId}`, {
      method: "DELETE",
    });
  }

  // Phase 13: Platform Analytics & Telemetry
  async getWorkspaceUsage(workspaceId: string): Promise<WorkspaceUsageSummary> {
    return this.request<WorkspaceUsageSummary>(`/analytics/workspace/${encodeURIComponent(workspaceId)}/usage`);
  }

  async getWorkspaceActivity(workspaceId: string, limit: number = 50): Promise<WorkspaceActivity> {
    return this.request<WorkspaceActivity>(`/analytics/workspace/${encodeURIComponent(workspaceId)}/activity?limit=${limit}`);
  }

  // Phase 14: Security, Auditing & Compliance
  async getWorkspaceAuditLogs(workspaceId: string, limit: number = 50, offset: number = 0): Promise<DocumentAuditResponse> {
    return this.request<DocumentAuditResponse>(
      `/analytics/workspace/${encodeURIComponent(workspaceId)}/audit-logs?limit=${limit}&offset=${offset}`
    );
  }

  async getWorkspaceSecurityIncidents(workspaceId: string, limit: number = 50, offset: number = 0): Promise<SecurityIncidentResponse> {
    return this.request<SecurityIncidentResponse>(
      `/analytics/workspace/${encodeURIComponent(workspaceId)}/security-incidents?limit=${limit}&offset=${offset}`
    );
  }

  async exportUserData(): Promise<any> {
    return this.request<any>("/users/me/export");
  }

  async deleteUserAccount(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>("/users/me", {
      method: "DELETE",
    });
  }
}

export const api = new ApiClient();
