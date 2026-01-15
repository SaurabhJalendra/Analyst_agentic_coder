import axios, { AxiosError } from 'axios';
import type { ChatRequest, ChatResponse, Session, ProgressData, Message, AuthToken, LoginRequest, RegisterRequest, User } from '../types';

// Use relative URLs so nginx can proxy to backend (works with any domain/IP)
const API_BASE_URL = '';

// Token storage keys
const TOKEN_KEY = 'coolbot_token';
const USER_KEY = 'coolbot_user';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 7200000, // 2 hours for very long-running tasks
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (unauthorized) - just clear tokens, don't redirect
// The App component handles showing login page based on auth state
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear stored auth data (but don't redirect - let App handle it)
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    return Promise.reject(error);
  }
);

// Retry configuration
const MAX_RETRIES = 2;
const RETRY_DELAY = 2000; // 2 seconds

// Helper to check if error is retryable
const isRetryableError = (error: AxiosError): boolean => {
  // Retry on network errors (no response)
  if (!error.response) return true;

  // Retry on server errors (5xx) except 500 (internal error)
  const status = error.response.status;
  return status === 502 || status === 503 || status === 504;
};

// Helper to wait
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Retry wrapper for API calls
async function withRetry<T>(
  operation: () => Promise<T>,
  retries: number = MAX_RETRIES
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;

      if (error instanceof AxiosError && isRetryableError(error) && attempt < retries) {
        console.log(`Request failed, retrying (${attempt + 1}/${retries})...`);
        await delay(RETRY_DELAY * (attempt + 1)); // Exponential backoff
        continue;
      }
      throw error;
    }
  }

  throw lastError;
}

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

// Chat API - with retry for network errors
export const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  return withRetry(async () => {
    const response = await api.post('/api/chat', request);
    return response.data;
  });
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

// Get all visualizations for a session
export const getSessionVisualizations = async (
  sessionId: string
): Promise<{ session_id: string; images: string[]; reports: string[]; base_url: string }> => {
  const response = await api.get(`/api/workspace/${sessionId}/visualizations`);
  return response.data;
};

// Utility to extract file paths from response text
export const extractFilePaths = (text: string): {
  images: string[];
  reports: string[];
  data: string[];
  code: string[];
  base64Images: string[];
} => {
  const files = {
    images: [] as string[],
    reports: [] as string[],
    data: [] as string[],
    code: [] as string[],
    base64Images: [] as string[],
  };

  // Patterns to match file paths in various formats
  const patterns = [
    // Match paths after common keywords
    /(?:Created|Generated|Saved|saved|Writing|Wrote|wrote|Output|output|File|file|Image|image|Chart|chart|Plot|plot|Figure|figure|saved to|written to|exported to)[:\s]+[`"']?([^\s\n`"']+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html|md|py|txt))[`"']?/gi,
    // Match paths in backticks
    /`([^\s`]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html|md|py|txt))`/gi,
    // Match paths after bullet points or dashes
    /[-•*]\s*([^\s\n]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html|md|py|txt))/gi,
    // Match paths with common output directories
    /((?:reports_output|output|charts|figures|images|plots|results|exports)[/\\][^\s\n"'`]+?\.(png|jpg|jpeg|gif|svg|html|csv|json|pdf|xlsx|xls))/gi,
    // Match relative paths starting with ./
    /(\.[/\\][^\s\n"'`]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html))/gi,
    // Match paths in quotes
    /["']([^"'\n]+?\.(png|jpg|jpeg|gif|svg|pdf|xlsx|xls|csv|json|html))["']/gi,
  ];

  // Extract base64 encoded images
  const base64Pattern = /data:image\/(png|jpeg|jpg|gif|svg\+xml);base64,([A-Za-z0-9+/=]+)/g;
  let base64Match;
  while ((base64Match = base64Pattern.exec(text)) !== null) {
    const fullDataUrl = base64Match[0];
    if (!files.base64Images.includes(fullDataUrl)) {
      files.base64Images.push(fullDataUrl);
    }
  }

  patterns.forEach((pattern) => {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      let filePath = match[1].replace(/\\/g, '/');

      // Clean up the path - remove leading ./ and any trailing punctuation
      filePath = filePath.replace(/^\.\//, '').replace(/[,;:)\]}>]+$/, '');

      // Skip absolute paths that include workspace (these need special handling)
      if (filePath.includes('/workspaces/')) {
        // Extract just the relative part after /repo/
        const repoMatch = filePath.match(/\/repo\/(.+)$/);
        if (repoMatch) {
          filePath = repoMatch[1];
        } else {
          continue; // Skip if we can't extract a relative path
        }
      }

      // Skip if path already has repo/ prefix (avoid duplication)
      if (filePath.startsWith('repo/')) {
        filePath = filePath.substring(5);
      }

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

// ============== Authentication APIs ==============

export const login = async (credentials: LoginRequest): Promise<AuthToken> => {
  const response = await api.post('/api/auth/login', credentials);
  const authData = response.data;

  // Store token and user data
  localStorage.setItem(TOKEN_KEY, authData.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(authData.user));

  return authData;
};

export const register = async (userData: RegisterRequest): Promise<AuthToken> => {
  const response = await api.post('/api/auth/register', userData);
  const authData = response.data;

  // Store token and user data
  localStorage.setItem(TOKEN_KEY, authData.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(authData.user));

  return authData;
};

export const logout = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getCurrentUser = (): User | null => {
  const userStr = localStorage.getItem(USER_KEY);
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }
  return null;
};

export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem(TOKEN_KEY);
};

export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const refreshToken = async (): Promise<AuthToken> => {
  const response = await api.post('/api/auth/refresh');
  const authData = response.data;

  // Update stored token
  localStorage.setItem(TOKEN_KEY, authData.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(authData.user));

  return authData;
};

export default api;
