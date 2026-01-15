import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Send, Loader2, AlertCircle, Keyboard } from 'lucide-react';

// Maximum message length (100KB should be plenty)
const MAX_MESSAGE_LENGTH = 100000;

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  placeholder?: string;
  disabled?: boolean;
}

export function ChatInput({ onSend, isLoading, placeholder = 'Ask me anything...', disabled = false }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [charWarning, setCharWarning] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleInputChange = (value: string) => {
    if (value.length > MAX_MESSAGE_LENGTH) {
      setCharWarning(true);
      setInput(value.slice(0, MAX_MESSAGE_LENGTH));
    } else {
      setCharWarning(false);
      setInput(value);
    }
  };

  const handleSend = () => {
    if (input.trim() && !isLoading && !disabled) {
      onSend(input.trim());
      setInput('');
      setCharWarning(false);
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isDisabled = isLoading || disabled;
  const canSend = input.trim() && !isDisabled;

  return (
    <div className="border-t border-dark-700/50 bg-dark-900/80 backdrop-blur-xl p-4">
      <div className="max-w-4xl mx-auto">
        {charWarning && (
          <div className="flex items-center gap-2 text-amber-400 text-sm mb-3 px-3 py-2 bg-amber-500/10 rounded-xl border border-amber-500/20">
            <AlertCircle size={16} />
            <span>Message truncated to {MAX_MESSAGE_LENGTH.toLocaleString()} characters</span>
          </div>
        )}
        <div className={`relative flex items-end gap-3 bg-dark-800/50 rounded-2xl border-2 transition-all duration-200 p-3 ${
          disabled
            ? 'border-red-500/30 bg-dark-900/30'
            : isFocused
              ? 'border-primary-500/50 shadow-lg shadow-primary-500/10'
              : 'border-dark-700/50 hover:border-dark-600'
        }`}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={disabled ? 'Disconnected from server...' : placeholder}
            disabled={isDisabled}
            rows={1}
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 resize-none outline-none px-2 py-1.5 min-h-[44px] max-h-[200px] disabled:opacity-50 text-base leading-relaxed"
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`flex-shrink-0 p-3 rounded-xl transition-all duration-200 ${
              canSend
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-400 hover:to-primary-500 text-white shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 active:scale-95'
                : 'bg-dark-700/50 text-slate-500 cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Send size={20} className={canSend ? 'translate-x-0.5 -translate-y-0.5' : ''} />
            )}
          </button>
        </div>
        <div className="flex justify-between items-center text-xs text-slate-500 mt-3 px-3">
          <div className="flex items-center gap-1.5">
            <Keyboard size={12} className="text-slate-600" />
            <span>Press <kbd className="px-1.5 py-0.5 bg-dark-700/50 rounded text-slate-400 font-mono text-xs">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 bg-dark-700/50 rounded text-slate-400 font-mono text-xs">Shift+Enter</kbd> for new line</span>
          </div>
          <span className={`font-mono transition-colors ${
            input.length > MAX_MESSAGE_LENGTH * 0.9
              ? 'text-amber-400'
              : input.length > MAX_MESSAGE_LENGTH * 0.7
                ? 'text-slate-400'
                : ''
          }`}>
            {input.length > 0 && `${input.length.toLocaleString()} / ${MAX_MESSAGE_LENGTH.toLocaleString()}`}
          </span>
        </div>
      </div>
    </div>
  );
}
