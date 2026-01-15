import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message, Session, ProgressData } from '../types';
import { sendMessage, getSessions, deleteSession, getSessionHistory, getProgress, isAuthenticated } from '../services/api';
import api from '../services/api';

// Connection status type
type ConnectionStatus = 'connected' | 'disconnected' | 'checking';

interface UseChatReturn {
  messages: Message[];
  sessions: Session[];
  currentSessionId: string | null;
  workspacePath: string | null;
  isLoading: boolean;
  progress: ProgressData | null;
  error: string | null;
  connectionStatus: ConnectionStatus;
  sendUserMessage: (content: string) => Promise<void>;
  startNewChat: () => void;
  switchSession: (sessionId: string) => Promise<void>;
  removeSession: (sessionId: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [workspacePath, setWorkspacePath] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking');

  const progressIntervalRef = useRef<number | null>(null);
  const connectionCheckRef = useRef<number | null>(null);

  // Check connection status (only if authenticated)
  const checkConnection = useCallback(async () => {
    if (!isAuthenticated()) {
      setConnectionStatus('disconnected');
      return;
    }
    try {
      await api.get('/api/sessions', { timeout: 5000 });
      setConnectionStatus('connected');
    } catch {
      setConnectionStatus('disconnected');
    }
  }, []);

  // Start connection monitoring
  useEffect(() => {
    checkConnection(); // Initial check
    connectionCheckRef.current = window.setInterval(checkConnection, 30000); // Check every 30s

    return () => {
      if (connectionCheckRef.current) {
        clearInterval(connectionCheckRef.current);
      }
    };
  }, [checkConnection]);

  // Cleanup progress polling
  const stopProgressPolling = useCallback(() => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    setProgress(null);
  }, []);

  // Start polling for progress
  const startProgressPolling = useCallback((sessionId: string) => {
    stopProgressPolling();

    const poll = async () => {
      try {
        const progressData = await getProgress(sessionId);
        if (progressData.status !== 'not_found') {
          setProgress(progressData);
        }
      } catch {
        // Ignore errors during polling
      }
    };

    poll(); // Initial poll
    progressIntervalRef.current = window.setInterval(poll, 1000);
  }, [stopProgressPolling]);

  // Load sessions on mount (only if authenticated)
  const refreshSessions = useCallback(async () => {
    if (!isAuthenticated()) {
      setSessions([]);
      return;
    }
    try {
      const sessionList = await getSessions();
      setSessions(sessionList);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopProgressPolling();
    };
  }, [stopProgressPolling]);

  // Send a message
  const sendUserMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Add user message immediately
    const userMessage: Message = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Add placeholder for assistant response
    const assistantPlaceholder: Message = {
      role: 'assistant',
      content: '',
      isStreaming: true,
    };
    setMessages(prev => [...prev, assistantPlaceholder]);

    // Start progress polling if we have a session
    if (currentSessionId) {
      startProgressPolling(currentSessionId);
    }

    try {
      const response = await sendMessage({
        message: content.trim(),
        session_id: currentSessionId,
        workspace_path: workspacePath,
      });

      // Update session state
      setCurrentSessionId(response.session_id);
      if (response.workspace_path) {
        setWorkspacePath(response.workspace_path);
      }

      // Replace placeholder with actual response
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIndex = newMessages.length - 1;
        if (newMessages[lastIndex]?.isStreaming) {
          newMessages[lastIndex] = {
            role: 'assistant',
            content: response.response,
            tool_calls: response.tool_calls,
            timestamp: new Date().toISOString(),
          };
        }
        return newMessages;
      });

      // Refresh sessions list
      await refreshSessions();

      // Start polling for progress on new session
      if (response.session_id !== currentSessionId) {
        startProgressPolling(response.session_id);
      }

    } catch (err) {
      // Parse error for better user feedback
      let errorMessage = 'Failed to send message';

      if (err instanceof Error) {
        const message = err.message.toLowerCase();

        if (message.includes('timeout') || message.includes('econnaborted')) {
          errorMessage = 'Request timed out. Claude Code is still processing - please wait and try again in a moment.';
        } else if (message.includes('network') || message.includes('econnrefused') || message.includes('enotfound')) {
          errorMessage = 'Network error. Please check your connection and try again.';
        } else if (message.includes('502') || message.includes('503') || message.includes('504')) {
          errorMessage = 'Server temporarily unavailable. Please try again in a few seconds.';
        } else if (message.includes('authentication') || message.includes('401')) {
          errorMessage = 'Authentication error. The server may need to re-authenticate with Claude.';
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);

      // Remove the placeholder message on error
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages[newMessages.length - 1]?.isStreaming) {
          newMessages.pop();
        }
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      stopProgressPolling();
    }
  }, [currentSessionId, workspacePath, isLoading, startProgressPolling, stopProgressPolling, refreshSessions]);

  // Start new chat
  const startNewChat = useCallback(() => {
    setMessages([]);
    setCurrentSessionId(null);
    setWorkspacePath(null);
    setError(null);
    stopProgressPolling();
  }, [stopProgressPolling]);

  // Switch to existing session
  const switchSession = useCallback(async (sessionId: string) => {
    if (sessionId === currentSessionId) return;

    setIsLoading(true);
    setError(null);
    stopProgressPolling();

    try {
      const history = await getSessionHistory(sessionId);
      setMessages(history);
      setCurrentSessionId(sessionId);

      // Get workspace path from session
      const session = sessions.find(s => s.id === sessionId);
      if (session?.workspace_path) {
        setWorkspacePath(session.workspace_path);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load session';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId, sessions, stopProgressPolling]);

  // Delete session
  const removeSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId);

      // If deleting current session, start new chat
      if (sessionId === currentSessionId) {
        startNewChat();
      }

      await refreshSessions();
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }, [currentSessionId, startNewChat, refreshSessions]);

  return {
    messages,
    sessions,
    currentSessionId,
    workspacePath,
    isLoading,
    progress,
    error,
    connectionStatus,
    sendUserMessage,
    startNewChat,
    switchSession,
    removeSession,
    refreshSessions,
  };
}
