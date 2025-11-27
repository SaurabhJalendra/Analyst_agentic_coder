import { Plus, MessageSquare, Trash2, RefreshCw } from 'lucide-react';
import { Session } from '../types';

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
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <aside className="w-72 bg-dark-800 border-r border-dark-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-dark-700">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          Cool Bot
        </h1>
      </div>

      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors"
        >
          <Plus size={20} />
          New Chat
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="flex items-center justify-between px-2 py-2 text-sm text-slate-400">
          <span>Conversations</span>
          <button
            onClick={onRefresh}
            className="p-1 hover:bg-dark-700 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No conversations yet.
            <br />
            Start a new chat!
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  currentSessionId === session.id
                    ? 'bg-primary-600/20 border border-primary-500/30'
                    : 'hover:bg-dark-700'
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <MessageSquare
                  size={16}
                  className={
                    currentSessionId === session.id
                      ? 'text-primary-400'
                      : 'text-slate-500'
                  }
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-200 truncate">
                    Chat {session.id.slice(0, 8)}...
                  </div>
                  <div className="text-xs text-slate-500">
                    {formatDate(session.created_at)} · {session.message_count} messages
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="p-1 opacity-0 group-hover:opacity-100 hover:bg-dark-600 rounded transition-all"
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
      <div className="p-4 border-t border-dark-700 text-center text-xs text-slate-500">
        Powered by Claude Code
      </div>
    </aside>
  );
}
