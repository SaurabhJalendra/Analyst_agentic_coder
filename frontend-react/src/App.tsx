import { useEffect, useRef, useState } from 'react';
import { Sidebar, ChatMessage, ChatInput, ProgressIndicator } from './components';
import { ConnectionStatus } from './components/ConnectionStatus';
import { VisualizationsPanel } from './components/VisualizationsPanel';
import Login from './components/Login';
import { useChat } from './hooks/useChat';
import { getCurrentUser, logout, isAuthenticated } from './services/api';
import { MessageSquarePlus, AlertCircle, LogOut, User as UserIcon, Code, FileText, GitBranch, BarChart3, Sparkles, ImageIcon } from 'lucide-react';
import type { User } from './types';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [showVisualizations, setShowVisualizations] = useState(false);

  const {
    messages,
    sessions,
    currentSessionId,
    isLoading,
    progress,
    error,
    connectionStatus,
    sendUserMessage,
    startNewChat,
    switchSession,
    removeSession,
    refreshSessions,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check authentication on mount
  useEffect(() => {
    if (isAuthenticated()) {
      const storedUser = getCurrentUser();
      setUser(storedUser);
    }
    setAuthChecked(true);
  }, []);

  // Auto-scroll to bottom when messages or progress change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, progress]);

  // Handle login success
  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    refreshSessions();
  };

  // Handle logout
  const handleLogout = () => {
    logout();
    setUser(null);
  };

  // Show loading while checking auth
  if (!authChecked) {
    return (
      <div className="flex h-screen bg-dark-950 items-center justify-center relative overflow-hidden">
        {/* Background gradient effects */}
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-500/20 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-emerald-500/20 rounded-full blur-3xl" />

        <div className="text-center relative z-10">
          <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-2xl flex items-center justify-center mb-6 mx-auto shadow-lg shadow-primary-500/25 animate-pulse">
            <Sparkles size={40} className="text-white" />
          </div>
          <div className="text-white text-lg font-medium">Loading...</div>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const features = [
    {
      icon: Code,
      title: 'Code Analysis',
      desc: 'Explore, understand, and refactor codebases with AI assistance',
      color: 'primary'
    },
    {
      icon: BarChart3,
      title: 'Generate Reports',
      desc: 'Run scripts and create visualizations from your data',
      color: 'emerald'
    },
    {
      icon: FileText,
      title: 'File Operations',
      desc: 'Read, write, and modify files across your project',
      color: 'blue'
    },
    {
      icon: GitBranch,
      title: 'Git Operations',
      desc: 'Clone repos, commit changes, and manage version control',
      color: 'purple'
    },
  ];

  const colorVariants = {
    primary: {
      bg: 'bg-primary-500/10',
      border: 'hover:border-primary-500/30',
      iconBg: 'bg-gradient-to-br from-primary-500 to-primary-600',
      iconShadow: 'shadow-primary-500/20',
    },
    emerald: {
      bg: 'bg-emerald-500/10',
      border: 'hover:border-emerald-500/30',
      iconBg: 'bg-gradient-to-br from-emerald-500 to-teal-600',
      iconShadow: 'shadow-emerald-500/20',
    },
    blue: {
      bg: 'bg-blue-500/10',
      border: 'hover:border-blue-500/30',
      iconBg: 'bg-gradient-to-br from-blue-500 to-blue-600',
      iconShadow: 'shadow-blue-500/20',
    },
    purple: {
      bg: 'bg-purple-500/10',
      border: 'hover:border-purple-500/30',
      iconBg: 'bg-gradient-to-br from-purple-500 to-purple-600',
      iconShadow: 'shadow-purple-500/20',
    },
  };

  return (
    <div className="flex h-screen bg-dark-950">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onNewChat={startNewChat}
        onSelectSession={switchSession}
        onDeleteSession={removeSession}
        onRefresh={refreshSessions}
      />

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-dark-700/50 bg-dark-900/80 backdrop-blur-xl">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {currentSessionId ? `Chat ${currentSessionId.slice(0, 8)}...` : 'New Conversation'}
            </h2>
            <p className="text-sm text-slate-500">
              {currentSessionId
                ? `${messages.length} messages`
                : 'Start by sending a message'}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <ConnectionStatus status={connectionStatus} />

            {/* View Visualizations Button */}
            {currentSessionId && (
              <button
                onClick={() => setShowVisualizations(true)}
                className="flex items-center gap-2 px-3 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded-xl text-sm text-purple-400 transition-all duration-200"
                title="View all generated charts and reports"
              >
                <ImageIcon size={16} />
                <span>Visualizations</span>
              </button>
            )}

            {/* User Menu */}
            <div className="flex items-center gap-3 pl-4 border-l border-dark-700/50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-500/20">
                  <UserIcon size={16} className="text-white" />
                </div>
                <span className="text-sm font-medium text-slate-300">{user.username}</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all duration-200"
                title="Logout"
              >
                <LogOut size={16} />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            // Welcome screen
            <div className="flex flex-col items-center justify-center h-full p-8 text-center relative overflow-hidden">
              {/* Background gradient effects */}
              <div className="absolute top-20 -right-20 w-60 h-60 bg-primary-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute bottom-20 -left-20 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

              <div className="relative z-10">
                <div className="w-24 h-24 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-3xl flex items-center justify-center mb-8 mx-auto shadow-2xl shadow-primary-500/30">
                  <MessageSquarePlus size={48} className="text-white" />
                </div>
                <h2 className="text-3xl font-bold text-white mb-3">
                  Welcome back, {user.username}!
                </h2>
                <p className="text-slate-400 max-w-lg mb-10 text-lg">
                  I'm your AI coding assistant powered by Claude Code. Here's what I can help you with:
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl w-full">
                  {features.map((feature, idx) => {
                    const colors = colorVariants[feature.color as keyof typeof colorVariants];
                    return (
                      <div
                        key={idx}
                        className={`${colors.bg} backdrop-blur-sm border border-dark-700/50 ${colors.border} rounded-2xl p-5 text-left transition-all duration-200 hover:scale-[1.02] cursor-default group`}
                      >
                        <div className={`w-12 h-12 ${colors.iconBg} rounded-xl flex items-center justify-center mb-4 shadow-lg ${colors.iconShadow} transition-transform duration-200 group-hover:scale-110`}>
                          <feature.icon size={24} className="text-white" />
                        </div>
                        <h3 className="font-semibold text-white text-lg mb-1.5">{feature.title}</h3>
                        <p className="text-sm text-slate-400 leading-relaxed">{feature.desc}</p>
                      </div>
                    );
                  })}
                </div>

                <p className="text-slate-500 text-sm mt-10">
                  Type a message below to get started
                </p>
              </div>
            </div>
          ) : (
            // Messages list
            <div className="divide-y divide-dark-700/30">
              {messages.map((message, index) => (
                <ChatMessage
                  key={index}
                  message={message}
                  sessionId={currentSessionId}
                />
              ))}

              {/* Progress Indicator - inside scrollable area */}
              {progress && (
                <div className="py-2">
                  <ProgressIndicator progress={progress} />
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mx-4 mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 backdrop-blur-sm">
            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="text-red-400" size={20} />
            </div>
            <div>
              <div className="text-sm font-semibold text-red-400">Error</div>
              <div className="text-sm text-red-300/80">{error}</div>
            </div>
          </div>
        )}

        {/* Chat Input */}
        <ChatInput
          onSend={sendUserMessage}
          isLoading={isLoading}
          disabled={connectionStatus === 'disconnected'}
          placeholder={
            currentSessionId
              ? 'Continue the conversation...'
              : 'Ask me anything about your code...'
          }
        />
      </main>

      {/* Visualizations Panel */}
      <VisualizationsPanel
        sessionId={currentSessionId}
        isOpen={showVisualizations}
        onClose={() => setShowVisualizations(false)}
      />
    </div>
  );
}

export default App;
