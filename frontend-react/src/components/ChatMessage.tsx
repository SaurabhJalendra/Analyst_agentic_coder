import { User, ChevronDown, Download, FileText, Image, Database, Code, Sparkles, Wrench } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../types';
import { extractFilePaths, getFileDownloadUrl } from '../services/api';
import { useState } from 'react';

interface ChatMessageProps {
  message: Message;
  sessionId: string | null;
}

export function ChatMessage({ message, sessionId }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());

  // Extract files from assistant messages
  const files = !isUser ? extractFilePaths(message.content) : null;
  const hasFiles = files && (files.images.length > 0 || files.reports.length > 0 || files.data.length > 0 || files.base64Images.length > 0);

  const toggleTool = (index: number) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  return (
    <div
      className={`message-enter flex gap-4 p-6 ${
        isUser
          ? 'bg-dark-800/30'
          : 'bg-gradient-to-r from-dark-900/50 to-dark-800/30'
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
          isUser
            ? 'bg-gradient-to-br from-primary-500 to-primary-600 shadow-primary-500/20'
            : 'bg-gradient-to-br from-emerald-500 to-teal-600 shadow-emerald-500/20'
        }`}
      >
        {isUser ? (
          <User size={20} className="text-white" />
        ) : (
          <Sparkles size={20} className="text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Role label */}
        <div className={`text-sm font-semibold mb-2 ${
          isUser ? 'text-primary-400' : 'text-emerald-400'
        }`}>
          {isUser ? 'You' : 'Analyst Agent'}
        </div>

        {/* Message content */}
        {message.isStreaming ? (
          <div className="flex items-center gap-3 py-2">
            <div className="flex gap-1.5">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-sm text-slate-400">Thinking...</span>
          </div>
        ) : (
          <div className="markdown-content text-slate-200 leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match;

                  if (isInline) {
                    return (
                      <code
                        className="bg-dark-700/70 px-2 py-1 rounded-md text-sm font-mono text-primary-300 border border-dark-600/50"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }

                  return (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      className="rounded-xl !my-4 !bg-dark-900/80 border border-dark-700/50"
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  );
                },
                a({ href, children }) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-400 hover:text-primary-300 underline decoration-primary-400/30 hover:decoration-primary-400 transition-colors"
                    >
                      {children}
                    </a>
                  );
                },
                p({ children }) {
                  return <p className="mb-4 last:mb-0">{children}</p>;
                },
                ul({ children }) {
                  return <ul className="list-disc list-inside mb-4 space-y-1">{children}</ul>;
                },
                ol({ children }) {
                  return <ol className="list-decimal list-inside mb-4 space-y-1">{children}</ol>;
                },
                h1({ children }) {
                  return <h1 className="text-xl font-bold text-white mb-3 mt-4">{children}</h1>;
                },
                h2({ children }) {
                  return <h2 className="text-lg font-bold text-white mb-2 mt-3">{children}</h2>;
                },
                h3({ children }) {
                  return <h3 className="text-base font-bold text-white mb-2 mt-3">{children}</h3>;
                },
                blockquote({ children }) {
                  return (
                    <blockquote className="border-l-4 border-primary-500/50 pl-4 my-4 text-slate-400 italic">
                      {children}
                    </blockquote>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-5 space-y-2">
            <div className="flex items-center gap-2 text-sm text-slate-400 font-medium">
              <Wrench size={14} className="text-primary-400" />
              {message.tool_calls.length} tool{message.tool_calls.length > 1 ? 's' : ''} used
            </div>
            {message.tool_calls.map((tool, index) => (
              <div
                key={index}
                className="bg-dark-800/50 rounded-xl border border-dark-700/50 overflow-hidden backdrop-blur-sm"
              >
                <button
                  onClick={() => toggleTool(index)}
                  className="w-full flex items-center justify-between p-3.5 text-left hover:bg-dark-700/30 transition-all duration-200"
                >
                  <span className="text-sm font-mono text-primary-400 flex items-center gap-2">
                    <Code size={14} />
                    {tool.name}
                  </span>
                  <ChevronDown
                    size={16}
                    className={`text-slate-500 transition-transform duration-200 ${
                      expandedTools.has(index) ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {expandedTools.has(index) && (
                  <div className="p-3.5 border-t border-dark-700/50 bg-dark-900/50">
                    <pre className="text-xs text-slate-400 overflow-x-auto font-mono">
                      {JSON.stringify(tool.input, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* File attachments */}
        {hasFiles && (
          <div className="mt-5 space-y-4">
            {/* Base64 Inline Images (no sessionId needed) */}
            {files.base64Images.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-300 font-semibold mb-3">
                  <div className="w-6 h-6 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Image size={14} className="text-purple-400" />
                  </div>
                  Generated Images ({files.base64Images.length})
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {files.base64Images.map((dataUrl, idx) => (
                    <div key={idx} className="bg-dark-800/50 rounded-xl p-3 border border-dark-700/50 hover:border-purple-500/30 transition-colors">
                      <img
                        src={dataUrl}
                        alt={`Generated image ${idx + 1}`}
                        className="w-full rounded-lg"
                      />
                      <a
                        href={dataUrl}
                        download={`image-${idx + 1}.png`}
                        className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 mt-2.5 font-medium transition-colors"
                      >
                        <Download size={12} />
                        Download image
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Workspace Images (requires sessionId) */}
            {sessionId && files.images.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-300 font-semibold mb-3">
                  <div className="w-6 h-6 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Image size={14} className="text-purple-400" />
                  </div>
                  Visualizations ({files.images.length})
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {files.images.map((path, idx) => (
                    <div key={idx} className="bg-dark-800/50 rounded-xl p-3 border border-dark-700/50 hover:border-purple-500/30 transition-colors">
                      <img
                        src={getFileDownloadUrl(sessionId, path)}
                        alt={path.split('/').pop()}
                        className="w-full rounded-lg"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <a
                        href={getFileDownloadUrl(sessionId, path)}
                        download
                        className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 mt-2.5 font-medium transition-colors"
                      >
                        <Download size={12} />
                        {path.split('/').pop()}
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reports (requires sessionId) */}
            {sessionId && files.reports.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-300 font-semibold mb-3">
                  <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <FileText size={14} className="text-blue-400" />
                  </div>
                  Reports ({files.reports.length})
                </div>
                <div className="space-y-2">
                  {files.reports.map((path, idx) => (
                    <a
                      key={idx}
                      href={getFileDownloadUrl(sessionId, path)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-3 bg-dark-800/50 rounded-xl border border-dark-700/50 hover:border-blue-500/30 hover:bg-dark-800 transition-all duration-200 group"
                    >
                      <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                        <FileText size={16} className="text-blue-400" />
                      </div>
                      <span className="text-sm text-slate-300 flex-1 truncate group-hover:text-white transition-colors">
                        {path.split('/').pop()}
                      </span>
                      <Download size={14} className="text-slate-500 group-hover:text-blue-400 transition-colors" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Data files (requires sessionId) */}
            {sessionId && files.data.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-300 font-semibold mb-3">
                  <div className="w-6 h-6 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                    <Database size={14} className="text-emerald-400" />
                  </div>
                  Data Files ({files.data.length})
                </div>
                <div className="space-y-2">
                  {files.data.map((path, idx) => (
                    <a
                      key={idx}
                      href={getFileDownloadUrl(sessionId, path)}
                      download
                      className="flex items-center gap-3 p-3 bg-dark-800/50 rounded-xl border border-dark-700/50 hover:border-emerald-500/30 hover:bg-dark-800 transition-all duration-200 group"
                    >
                      <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                        <Database size={16} className="text-emerald-400" />
                      </div>
                      <span className="text-sm text-slate-300 flex-1 truncate group-hover:text-white transition-colors">
                        {path.split('/').pop()}
                      </span>
                      <Download size={14} className="text-slate-500 group-hover:text-emerald-400 transition-colors" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Code files (requires sessionId) */}
            {sessionId && files.code.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-300 font-semibold mb-3">
                  <div className="w-6 h-6 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                    <Code size={14} className="text-yellow-400" />
                  </div>
                  Code Files ({files.code.length})
                </div>
                <div className="space-y-2">
                  {files.code.map((path, idx) => (
                    <a
                      key={idx}
                      href={getFileDownloadUrl(sessionId, path)}
                      download
                      className="flex items-center gap-3 p-3 bg-dark-800/50 rounded-xl border border-dark-700/50 hover:border-yellow-500/30 hover:bg-dark-800 transition-all duration-200 group"
                    >
                      <div className="w-8 h-8 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                        <Code size={16} className="text-yellow-400" />
                      </div>
                      <span className="text-sm text-slate-300 flex-1 truncate group-hover:text-white transition-colors">
                        {path.split('/').pop()}
                      </span>
                      <Download size={14} className="text-slate-500 group-hover:text-yellow-400 transition-colors" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
