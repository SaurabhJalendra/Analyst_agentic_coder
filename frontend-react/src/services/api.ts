import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || '';

const http = axios.create({ baseURL: BASE, timeout: 30_000 });

export interface ChatResponse {
  session_id: string;
  event_stream_url: string;
}

export async function postChat(message: string, sessionId: string | null, workspacePath?: string): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/api/chat', {
    message,
    session_id: sessionId,
    workspace_path: workspacePath,
  });
  return data;
}

export async function listSessions() {
  const { data } = await http.get('/api/sessions');
  return data.sessions ?? data;
}

export async function deleteSession(id: string) {
  await http.delete(`/api/sessions/${id}`);
}

export async function getHistory(id: string) {
  const { data } = await http.get(`/api/session/${id}/history`);
  return data;
}

export function eventStreamUrl(sessionId: string): string {
  return `${BASE}/api/chat/stream/${sessionId}`;
}
