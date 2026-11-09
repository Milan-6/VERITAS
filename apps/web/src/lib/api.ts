import { DocumentItem, DocumentDetail, DocumentProcessingJob, User } from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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

    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
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
  ): Promise<{ document: DocumentItem; job: DocumentProcessingJob }> {
    const formData = new FormData();
    formData.append("file", file);

    const token = this.getToken();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/documents/upload`);
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

  async listDocuments(status?: string): Promise<DocumentItem[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.request<DocumentItem[]>(`/documents${query}`);
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
    return `${API_BASE_URL}/documents/${id}/download`;
  }
}

export const api = new ApiClient();
