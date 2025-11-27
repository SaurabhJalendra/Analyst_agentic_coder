import { useEffect, useRef } from 'react';
import { Sidebar, ChatMessage, ChatInput, ProgressIndicator } from './components';
import { useChat } from './hooks/useChat';
import { MessageSquarePlus, AlertCircle } from 'lucide-react';

function App() {
  const {
    messages,
    sessions,
    currentSessionId,
    isLoading,
    progress,
    error,
    sendUserMessage,
    startNewChat,
    switchSession,
    removeSession,
    refreshSessions,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
        <header className="flex items-center justify-between px-6 py-4 border-b border-dark-700 bg-dark-800">
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
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            // Welcome screen
            <div className="flex flex-col items-center justify-center h-full p-8 text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-2xl flex items-center justify-center mb-6">
                <MessageSquarePlus size={40} className="text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Welcome to Cool Bot
              </h2>
              <p className="text-slate-400 max-w-md mb-8">
                I'm your AI coding assistant powered by Claude Code. I can help you with:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl w-full">
                {[
                  { title: 'Code Analysis', desc: 'Explore and understand codebases' },
                  { title: 'Generate Reports', desc: 'Run scripts and generate visualizations' },
                  { title: 'File Operations', desc: 'Read, write, and modify files' },
                  { title: 'Git Operations', desc: 'Clone repos and manage version control' },
                ].map((feature, idx) => (
                  <div
                    key={idx}
                    className="bg-dark-800 border border-dark-700 rounded-lg p-4 text-left hover:border-primary-500/30 transition-colors"
                  >
                    <h3 className="font-medium text-slate-200 mb-1">{feature.title}</h3>
                    <p className="text-sm text-slate-500">{feature.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            // Messages list
            <div className="divide-y divide-dark-700/50">
              {messages.map((message, index) => (
                <ChatMessage
                  key={index}
                  message={message}
                  sessionId={currentSessionId}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Progress Indicator */}
        {progress && <ProgressIndicator progress={progress} />}

        {/* Error Message */}
        {error && (
          <div className="mx-4 mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3">
            <AlertCircle className="text-red-400 flex-shrink-0" size={20} />
            <div>
              <div className="text-sm font-medium text-red-400">Error</div>
              <div className="text-sm text-red-300/80">{error}</div>
            </div>
          </div>
        )}

        {/* Chat Input */}
        <ChatInput
          onSend={sendUserMessage}
          isLoading={isLoading}
          placeholder={
            currentSessionId
              ? 'Continue the conversation...'
              : 'Ask me anything about your code...'
          }
        />
      </main>
    </div>
  );
}

export default App;
