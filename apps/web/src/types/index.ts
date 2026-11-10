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

export interface SynthesisPoint {
  topic: string;
  summary: string;
  source_excerpt?: string | null;
  page_number?: number | null;
  section_title?: string | null;
  confidence_score: number;
}

export interface PaperSynthesis {
  document_id: string;
  document_title: string;
  problem_statement: SynthesisPoint;
  methodology: SynthesisPoint;
  dataset_used: SynthesisPoint;
  key_results: SynthesisPoint;
  limitations: SynthesisPoint;
  created_at: string;
}

export interface MatrixColumn {
  document_id: string;
  document_title: string;
  problem_statement: string;
  methodology: string;
  dataset_used: string;
  key_results: string;
  limitations: string;
}

export interface MatrixContradiction {
  aspect: string;
  paper_a_id: string;
  paper_a_title: string;
  paper_b_id: string;
  paper_b_title: string;
  description: string;
  divergence_level: "HIGH" | "MEDIUM" | "LOW";
}

export interface LiteratureMatrix {
  topic_query?: string | null;
  document_count: number;
  columns: MatrixColumn[];
  contradictions_and_divergences: MatrixContradiction[];
  generated_at: string;
}

export interface ExternalPaperMetadata {
  id: string;
  title: string;
  authors: string[];
  publication_year?: number | null;
  abstract?: string | null;
  doi?: string | null;
  landing_page_url?: string | null;
  pdf_url?: string | null;
  is_open_access: boolean;
  citation_count: number;
  venue?: string | null;
  source: string;
}

export interface DiscoverySearchResponse {
  query: string;
  total_results: number;
  page: number;
  per_page: number;
  results: ExternalPaperMetadata[];
}

export interface DirectIngestResponse {
  document_id: string;
  job_id: string;
  filename: string;
  title: string;
  status: string;
  message: string;
}

export interface CitationNetworkResponse {
  document_id: string;
  document_title: string;
  doi?: string | null;
  citation_count: number;
  references: ExternalPaperMetadata[];
  cited_by: ExternalPaperMetadata[];
  top_related: ExternalPaperMetadata[];
}

export interface GraphNode {
  id: string;
  tenant_id: string;
  type: "Paper" | "Author" | "Dataset" | "Algorithm" | "Metric" | "Concept" | string;
  label: string;
  description?: string | null;
  document_id?: string | null;
}

export interface GraphEdge {
  id: string;
  tenant_id: string;
  source_node_id: string;
  target_node_id: string;
  relationship_type: string;
  provenance_chunk_id?: string | null;
  source_excerpt?: string | null;
  document_id?: string | null;
}

export interface WorkspaceGraph {
  tenant_id: string;
  total_nodes: number;
  total_edges: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AgentEvent {
  status: "thinking" | "tool_call" | "generating_report" | "verifying" | "completed" | "error";
  step?: number;
  thought?: string;
  action?: string;
  tool?: string;
  args?: any;
  output_preview?: string;
  evidence_count?: number;
  message?: string;
  report?: string;
  verification_report?: VerificationReport | null;
  steps_taken?: number;
}

export interface Flashcard {
  id: string;
  deck_id: string;
  front_concept: string;
  back_definition: string;
  source_citation?: string | null;
  page_number?: number | null;
  section_title?: string | null;
  source_excerpt?: string | null;
  created_at: string;
}

export interface FlashcardDeck {
  id: string;
  tenant_id: string;
  document_id: string;
  title: string;
  card_count: number;
  created_at: string;
  updated_at: string;
  cards: Flashcard[];
}

export interface QuizQuestion {
  question_id: string;
  question_text: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  source_citation?: string | null;
  page_number?: number | null;
}

export interface Quiz {
  id: string;
  tenant_id: string;
  document_id: string;
  title: string;
  total_questions: number;
  created_at: string;
  updated_at: string;
  questions: QuizQuestion[];
}

export interface QuizQuestionResult {
  question_id: string;
  question_text: string;
  user_answer?: string | null;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
  source_citation?: string | null;
  page_number?: number | null;
}

export interface QuizEvaluationResult {
  quiz_id: string;
  document_id: string;
  score: number;
  total_questions: number;
  percentage: number;
  results: QuizQuestionResult[];
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  email: string;
  full_name?: string | null;
  role: "OWNER" | "EDITOR" | "VIEWER" | string;
  joined_at: string;
}

export interface WorkspaceItem {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  role?: "OWNER" | "EDITOR" | "VIEWER" | string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceDetail extends WorkspaceItem {
  members: WorkspaceMember[];
  document_count: number;
}

export interface IntegrationStatus {
  id: string;
  provider: string;
  external_user_id?: string | null;
  is_active: boolean;
  workspace_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebhookSubscriptionItem {
  id: string;
  workspace_id: string;
  url: string;
  events_subscribed: string[];
  secret_key: string;
  is_active: boolean;
  description?: string | null;
  created_at: string;
}

export interface ZoteroSyncSummary {
  status: string;
  provider: string;
  total_items_fetched: number;
  synced_references: number;
  documents_created: number;
  skipped_or_existing: number;
}

export interface LlmFeatureUsage {
  tokens: number;
  cost_usd: number;
  calls: number;
}

export interface LlmUsageSummary {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  total_llm_invocations: number;
  breakdown_by_feature: Record<string, LlmFeatureUsage>;
}

export interface WorkspaceUsageSummary {
  workspace_id: string;
  total_documents: number;
  total_api_requests: number;
  llm_usage: LlmUsageSummary;
}

export interface ActivityRecord {
  id: string;
  endpoint: string;
  method: string;
  status_code: number;
  response_time_ms: number;
  timestamp: string;
}

export interface WorkspaceActivity {
  workspace_id: string;
  total_requests: number;
  average_response_time_ms: number;
  error_rate_percentage: number;
  recent_activity: ActivityRecord[];
}

// Phase 14: Security, Auditing & Compliance
export interface DocumentAuditItem {
  id: string;
  document_id: string;
  document_title: string;
  workspace_id?: string | null;
  user_id?: string | null;
  action: string;
  ip_address?: string | null;
  timestamp: string;
}

export interface SecurityIncidentItem {
  id: string;
  workspace_id?: string | null;
  user_id?: string | null;
  incident_type: string;
  severity: string;
  details: Record<string, any>;
  ip_address?: string | null;
  timestamp: string;
}

export interface DocumentAuditResponse {
  workspace_id: string;
  total: number;
  items: DocumentAuditItem[];
}

export interface SecurityIncidentResponse {
  workspace_id: string;
  total: number;
  items: SecurityIncidentItem[];
}





