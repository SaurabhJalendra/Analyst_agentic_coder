import { Plus, MessageSquare, Trash2, RefreshCw, Sparkles, Clock, Hash } from 'lucide-react';
import type { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRefresh: () => void;
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onRefresh,
}: SidebarProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <aside className="w-72 bg-dark-900/95 backdrop-blur-xl border-r border-dark-700/50 flex flex-col h-full relative overflow-hidden">
      {/* Background gradient accent */}
      <div className="absolute -top-20 -left-20 w-40 h-40 bg-primary-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 -right-20 w-40 h-40 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="p-5 border-b border-dark-700/50 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
            <Sparkles size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Analyst Agent</h1>
            <p className="text-xs text-slate-500">AI-Powered Coding</p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-4 relative z-10">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-400 hover:to-primary-500 text-white rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 active:scale-[0.98]"
        >
          <Plus size={20} />
          New Chat
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 relative z-10">
        <div className="flex items-center justify-between px-2 py-2 mb-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Conversations</span>
          <button
            onClick={onRefresh}
            className="p-1.5 hover:bg-dark-700/50 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
            title="Refresh"
          >
            <RefreshCw size={14} className="text-slate-500 hover:text-slate-300" />
          </button>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="w-16 h-16 mx-auto mb-4 bg-dark-800/50 rounded-2xl flex items-center justify-center">
              <MessageSquare size={28} className="text-slate-600" />
            </div>
            <p className="text-slate-400 text-sm font-medium mb-1">No conversations yet</p>
            <p className="text-slate-600 text-xs">Start a new chat to begin</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group relative flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200 ${
                  currentSessionId === session.id
                    ? 'bg-gradient-to-r from-primary-500/15 to-emerald-500/10 border border-primary-500/30 shadow-lg shadow-primary-500/10'
                    : 'hover:bg-dark-800/50 border border-transparent'
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                  currentSessionId === session.id
                    ? 'bg-primary-500/20'
                    : 'bg-dark-700/50 group-hover:bg-dark-700'
                }`}>
                  <MessageSquare
                    size={16}
                    className={
                      currentSessionId === session.id
                        ? 'text-primary-400'
                        : 'text-slate-500 group-hover:text-slate-400'
                    }
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-medium truncate transition-colors ${
                    currentSessionId === session.id
                      ? 'text-white'
                      : 'text-slate-300 group-hover:text-white'
                  }`}>
                    Chat {session.id.slice(0, 8)}
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                      <Clock size={10} />
                      {formatDate(session.created_at)}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                      <Hash size={10} />
                      {session.message_count}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded-lg transition-all duration-200"
                  title="Delete"
                >
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-dark-700/50 relative z-10">
        <p className="text-center text-xs text-slate-500">
          Powered by <span className="text-primary-400 font-medium">Claude Code</span>
        </p>
      </div>
    </aside>
  );
}
