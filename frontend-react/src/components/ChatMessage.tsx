import { User, Bot, ChevronDown, Download, FileText, Image, Database, Code } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message } from '../types';
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
  const hasFiles = files && (files.images.length > 0 || files.reports.length > 0 || files.data.length > 0);

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
      className={`message-enter flex gap-4 p-4 ${
        isUser ? 'bg-dark-800/50' : 'bg-dark-900/50'
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-primary-600' : 'bg-emerald-600'
        }`}
      >
        {isUser ? (
          <User size={18} className="text-white" />
        ) : (
          <Bot size={18} className="text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Role label */}
        <div className="text-sm font-medium text-slate-400 mb-1">
          {isUser ? 'You' : 'Cool Bot'}
        </div>

        {/* Message content */}
        {message.isStreaming ? (
          <div className="flex items-center gap-2 text-slate-400">
            <div className="flex gap-1">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
            <span className="text-sm">Thinking...</span>
          </div>
        ) : (
          <div className="markdown-content text-slate-200">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match;

                  if (isInline) {
                    return (
                      <code
                        className="bg-dark-700 px-1.5 py-0.5 rounded text-sm font-mono text-primary-300"
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
                      className="rounded-lg !my-4 !bg-dark-900"
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
                      className="text-primary-400 hover:text-primary-300 underline"
                    >
                      {children}
                    </a>
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
          <div className="mt-4 space-y-2">
            <div className="text-sm text-slate-400 font-medium">
              🔧 {message.tool_calls.length} tool(s) used
            </div>
            {message.tool_calls.map((tool, index) => (
              <div
                key={index}
                className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden"
              >
                <button
                  onClick={() => toggleTool(index)}
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-dark-700/50 transition-colors"
                >
                  <span className="text-sm font-mono text-primary-400">
                    {tool.name}
                  </span>
                  <ChevronDown
                    size={16}
                    className={`text-slate-500 transition-transform ${
                      expandedTools.has(index) ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {expandedTools.has(index) && (
                  <div className="p-3 border-t border-dark-700 bg-dark-900">
                    <pre className="text-xs text-slate-400 overflow-x-auto">
                      {JSON.stringify(tool.input, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* File attachments */}
        {hasFiles && sessionId && (
          <div className="mt-4 space-y-4">
            {/* Images */}
            {files.images.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-400 font-medium mb-2">
                  <Image size={16} />
                  Visualizations ({files.images.length})
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {files.images.map((path, idx) => (
                    <div key={idx} className="bg-dark-800 rounded-lg p-2 border border-dark-700">
                      <img
                        src={getFileDownloadUrl(sessionId, path)}
                        alt={path.split('/').pop()}
                        className="w-full rounded"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <a
                        href={getFileDownloadUrl(sessionId, path)}
                        download
                        className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300 mt-2"
                      >
                        <Download size={12} />
                        {path.split('/').pop()}
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reports */}
            {files.reports.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-400 font-medium mb-2">
                  <FileText size={16} />
                  Reports ({files.reports.length})
                </div>
                <div className="space-y-1">
                  {files.reports.map((path, idx) => (
                    <a
                      key={idx}
                      href={getFileDownloadUrl(sessionId, path)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 p-2 bg-dark-800 rounded-lg border border-dark-700 hover:border-primary-500/30 transition-colors"
                    >
                      <FileText size={16} className="text-primary-400" />
                      <span className="text-sm text-slate-300 flex-1 truncate">
                        {path.split('/').pop()}
                      </span>
                      <Download size={14} className="text-slate-500" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Data files */}
            {files.data.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-400 font-medium mb-2">
                  <Database size={16} />
                  Data Files ({files.data.length})
                </div>
                <div className="space-y-1">
                  {files.data.map((path, idx) => (
                    <a
                      key={idx}
                      href={getFileDownloadUrl(sessionId, path)}
                      download
                      className="flex items-center gap-2 p-2 bg-dark-800 rounded-lg border border-dark-700 hover:border-primary-500/30 transition-colors"
                    >
                      <Database size={16} className="text-emerald-400" />
                      <span className="text-sm text-slate-300 flex-1 truncate">
                        {path.split('/').pop()}
                      </span>
                      <Download size={14} className="text-slate-500" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Code files */}
            {files.code.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-400 font-medium mb-2">
                  <Code size={16} />
                  Code Files ({files.code.length})
                </div>
                <div className="space-y-1">
                  {files.code.map((path, idx) => (
                    <a
                      key={idx}
                      href={getFileDownloadUrl(sessionId, path)}
                      download
                      className="flex items-center gap-2 p-2 bg-dark-800 rounded-lg border border-dark-700 hover:border-primary-500/30 transition-colors"
                    >
                      <Code size={16} className="text-yellow-400" />
                      <span className="text-sm text-slate-300 flex-1 truncate">
                        {path.split('/').pop()}
                      </span>
                      <Download size={14} className="text-slate-500" />
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
