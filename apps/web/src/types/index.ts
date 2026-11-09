export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DocumentMetadata {
  id: string;
  document_id: string;
  title: string;
  authors?: string[];
  abstract?: string | null;
  keywords?: string[];
  publication_date?: string | null;
  doi?: string | null;
  journal_or_conference?: string | null;
  total_pages: number;
  raw_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentProcessingJob {
  id: string;
  document_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
  stage: string;
  progress_pct: number;
  attempts: number;
  max_retries: number;
  error_details?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedPage {
  id: string;
  document_id: string;
  page_number: number;
  width: number;
  height: number;
  text_length: number;
  has_images: boolean;
  has_tables: boolean;
}

export interface ExtractedSection {
  id: string;
  document_id: string;
  section_title: string;
  section_level: number;
  start_page: number;
  end_page: number;
  order_index: number;
}

export interface ExtractedContent {
  id: string;
  document_id: string;
  chunk_id: string;
  content_type: "paragraph" | "header" | "table" | "figure_caption" | "math_expression" | "reference";
  source_text: string;
  page_number: number;
  section: string;
  subsection?: string | null;
  extraction_method: string;
  bounding_box?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  } | null;
  order_index: number;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  workspace_id?: string | null;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  file_hash_sha256: string;
  status: "UPLOADED" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  metadata?: DocumentMetadata | null;
  latest_job?: DocumentProcessingJob | null;
}

export interface DocumentDetail extends DocumentItem {
  extracted_pages: ExtractedPage[];
  extracted_sections: ExtractedSection[];
  extracted_contents: ExtractedContent[];
}

export interface SearchResultChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number: number;
  section_title: string;
  subsection?: string | null;
  content_text: string;
  score: number;
  dense_score?: number | null;
  sparse_score?: number | null;
}

export interface SearchResponse {
  query: string;
  tenant_id: string;
  total_results: number;
  results: SearchResultChunk[];
}

export interface Citation {
  document_id: string;
  document_title: string;
  page_number: number;
  section_title: string;
  chunk_id: string;
  score?: number | null;
}

export interface VerifiedClaim {
  claim_id: string;
  claim_text: string;
  status: "SUPPORTED" | "CONTRADICTED" | "MISSING";
  document_id?: string | null;
  document_title?: string | null;
  page_number?: number | null;
  section_title?: string | null;
  chunk_id?: string | null;
  source_excerpt?: string | null;
  reasoning?: string | null;
}

export interface VerificationReport {
  overall_status: "VERIFIED" | "PARTIALLY_VERIFIED" | "UNVERIFIED" | "ABSTAINED";
  claims: VerifiedClaim[];
  supported_count: number;
  contradicted_count: number;
  missing_count: number;
  verification_score: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[] | null;
  verification_report?: VerificationReport | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  workspace_id?: string | null;
  document_id?: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}
