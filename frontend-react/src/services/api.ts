import axios from 'axios';
import { ChatRequest, ChatResponse, Session, ProgressData, Message } from '../types';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes for long-running tasks
  headers: {
    'Content-Type': 'application/json',
  },
});

// Session APIs
export const getSessions = async (): Promise<Session[]> => {
  const response = await api.get('/api/sessions');
  return response.data.sessions || [];
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/api/sessions/${sessionId}`);
};

export const getSessionHistory = async (sessionId: string): Promise<Message[]> => {
  const response = await api.get(`/api/session/${sessionId}/history`);
  return response.data.messages || [];
};

// Chat API
export const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post('/api/chat', request);
  return response.data;
};

// Progress API
export const getProgress = async (sessionId: string): Promise<ProgressData> => {
  try {
    const response = await api.get(`/api/progress/${sessionId}`);
    return response.data;
  } catch {
    return { status: 'not_found' };
  }
};

// File APIs
export const getFileDownloadUrl = (sessionId: string, filePath: string): string => {
  const normalizedPath = filePath.replace(/\\/g, '/').replace(/^\//, '');
  return `${API_BASE_URL}/api/workspace/${sessionId}/files/repo/${normalizedPath}`;
};

export const listWorkspaceDirectory = async (
  sessionId: string,
  directoryPath: string = ''
): Promise<{ files: Array<{ name: string; path: string; is_dir: boolean; size?: number }> }> => {
  const response = await api.get(`/api/workspace/${sessionId}/list/${directoryPath}`);
  return response.data;
};

// Utility to extract file paths from response text
export const extractFilePaths = (text: string): {
  images: string[];
  reports: string[];
  data: string[];
  code: string[];
} => {
  const files = {
    images: [] as string[],
    reports: [] as string[],
    data: [] as string[],
    code: [] as string[],
  };

  const patterns = [
    /(?:Created|Generated|Saved to|Writing to|Wrote|output\/|reports\/|charts\/|data\/)([^\s\n]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html|md|py|txt))/gi,
    /`([^\s`]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html|md|py|txt))`/gi,
    /- ([^\s\n]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html|md|py|txt))/gi,
    /((?:reports_output|output|charts)[/\\][^\s\n]+?\.(png|jpg|jpeg|gif|svg|html|csv|json|pdf))/gi,
  ];

  patterns.forEach((pattern) => {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const filePath = match[1].replace(/\\/g, '/');
      const ext = filePath.split('.').pop()?.toLowerCase() || '';

      if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(ext)) {
        if (!files.images.includes(filePath)) files.images.push(filePath);
      } else if (['pdf', 'xlsx', 'xls', 'html', 'md'].includes(ext)) {
        if (!files.reports.includes(filePath)) files.reports.push(filePath);
      } else if (['csv', 'json'].includes(ext)) {
        if (!files.data.includes(filePath)) files.data.push(filePath);
      } else if (['py', 'txt'].includes(ext)) {
        if (!files.code.includes(filePath)) files.code.push(filePath);
      }
    }
  });

  return files;
};

export default api;
