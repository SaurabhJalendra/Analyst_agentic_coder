// Authentication types
export interface User {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

// Session types
export interface Session {
  id: string;
  created_at: string;
  message_count: number;
  workspace_path?: string;
  active_repo?: string;
}

// Message types
export interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  tool_calls?: ToolCall[];
  isStreaming?: boolean;
}

export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
  output?: string;
  status?: 'pending' | 'running' | 'completed' | 'error';
}

// API request/response types
export interface ChatRequest {
  message: string;
  session_id?: string | null;
  workspace_path?: string | null;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  tool_calls: ToolCall[];
  requires_approval: boolean;
  workspace_path?: string;
}

export interface ProgressStep {
  step: string;
  details?: string;
  timestamp?: string;
}

export interface ProgressData {
  status: 'not_found' | 'in_progress' | 'completed' | 'error';
  current_step?: string;
  iteration?: number;
  max_iterations?: number;
  steps?: ProgressStep[];
  error?: string;
}

// File types
export interface FileInfo {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  download_url?: string;
}

export interface ExtractedFiles {
  images: string[];
  reports: string[];
  data: string[];
  code: string[];
  other: string[];
}
