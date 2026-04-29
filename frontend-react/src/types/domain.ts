export interface Session {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface PlanStep {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'done';
  durationMs?: number;
  startedAt?: number;
}

export interface AgentState {
  id: string;
  parentId?: string;
  kind: string;
  model: string;
  status: 'running' | 'queued' | 'done';
  tokens: number;
  durationMs?: number;
  result?: string;
  toolsUsed: string[];
}

export interface Artifact {
  id: string;
  kind: 'chart' | 'table' | 'code' | 'report' | 'file';
  title: string;
  sourceAttribution: string;
  methodologyId: string;
  createdAt: number;
}

export interface SourceAccess {
  source: string;
  callCount: number;
  lastOp?: string;
}

export interface ActivityEntry {
  id: number;
  ts: number;
  category: 'plan' | 'tool' | 'subagent' | 'skill' | 'memory' | 'source' | 'message' | 'thinking' | 'error' | 'other';
  text: string;
  meta?: Record<string, unknown>;
}

export interface UserMessage { kind: 'user'; id: string; text: string; ts: number; }
export interface AssistantMessage { kind: 'assistant'; id: string; text: string; ts: number; }
export interface ArtifactMessage { kind: 'artifact'; id: string; artifact: Artifact; ts: number; }
export interface ThinkingMessage { kind: 'thinking'; id: string; tokens: number; preview: string; ts: number; }
export interface SubAgentMessage { kind: 'subagent'; id: string; agentId: string; subKind: string; status: AgentState['status']; statusText?: string; ts: number; }

export type ChatTurn = UserMessage | AssistantMessage | ArtifactMessage | ThinkingMessage | SubAgentMessage;
