import { useState, useEffect, useCallback } from "react";
import { DocumentTreeData, DocumentTreeNode, DocumentTreeLink } from "../data/types";
import mockTreeRaw from "../data/mock_document_tree.json";

export interface UseDocumentDataOptions {
  endpoint?: string;
  documentId?: string;
  timeoutMs?: number;
  autoFetch?: boolean;
}

export interface UseDocumentDataReturn {
  data: DocumentTreeData;
  isLoading: boolean;
  error: string | null;
  isFallback: boolean;
  refetch: () => Promise<void>;
}

const getBaseUrl = (): string => {
  const env = (import.meta as any).env;
  if (env?.VITE_API_BASE_URL) {
    const base = env.VITE_API_BASE_URL.replace(/\/+$/, "");
    return `${base}/api/v1/document/tree`;
  }
  if (env?.VITE_API_URL) {
    return env.VITE_API_URL;
  }
  return "http://localhost:8000/api/v1/document/tree";
};

const DEFAULT_ENDPOINT = getBaseUrl();

export function useDocumentData(options: UseDocumentDataOptions = {}): UseDocumentDataReturn {
  const {
    endpoint = DEFAULT_ENDPOINT,
    documentId,
    timeoutMs = 2500,
    autoFetch = true,
  } = options;

  const [data, setData] = useState<DocumentTreeData>(() => ({
    nodes: mockTreeRaw.nodes as DocumentTreeNode[],
    links: mockTreeRaw.links as DocumentTreeLink[],
  }));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFallback, setIsFallback] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const targetUrl = documentId ? `${endpoint}?document_id=${encodeURIComponent(documentId)}` : endpoint;

    try {
      const response = await fetch(targetUrl, {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();

      // Validate schema compliance: must contain nodes and links arrays
      if (!Array.isArray(json?.nodes) || !Array.isArray(json?.links)) {
        throw new Error("Invalid schema received: missing 'nodes' or 'links' array.");
      }

      setData({
        nodes: json.nodes,
        links: json.links,
      });
      setIsFallback(false);
      console.info(`[VERITAS Graph] Live document tree ingested successfully from ${targetUrl} (${json.nodes.length} nodes).`);
    } catch (err: any) {
      clearTimeout(timeoutId);
      const isAbort = err.name === "AbortError";
      const errMsg = isAbort
        ? `Connection to live API timed out after ${timeoutMs}ms.`
        : err.message || "Failed to reach backend endpoint.";

      console.warn(`[VERITAS Graph] Live API unreachable (${errMsg}). Falling back to local mock hierarchy.`);
      setError(errMsg);
      setIsFallback(true);
      setData({
        nodes: mockTreeRaw.nodes as DocumentTreeNode[],
        links: mockTreeRaw.links as DocumentTreeLink[],
      });
    } finally {
      setIsLoading(false);
    }
  }, [endpoint, documentId, timeoutMs]);

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }
  }, [autoFetch, fetchData]);

  return {
    data,
    isLoading,
    error,
    isFallback,
    refetch: fetchData,
  };
}
