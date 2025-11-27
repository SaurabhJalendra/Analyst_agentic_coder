import { Loader2, CheckCircle, AlertCircle, ChevronDown } from 'lucide-react';
import { ProgressData } from '../types';
import { useState } from 'react';

interface ProgressIndicatorProps {
  progress: ProgressData;
}

export function ProgressIndicator({ progress }: ProgressIndicatorProps) {
  const [expanded, setExpanded] = useState(false);

  if (progress.status === 'not_found') {
    return null;
  }

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'completed':
        return <CheckCircle className="text-emerald-400" size={18} />;
      case 'error':
        return <AlertCircle className="text-red-400" size={18} />;
      default:
        return <Loader2 className="text-primary-400 animate-spin" size={18} />;
    }
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-lg mx-4 mb-4 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3 hover:bg-dark-700/50 transition-colors"
      >
        {getStatusIcon()}
        <div className="flex-1 text-left">
          <div className="text-sm font-medium text-slate-200">
            {progress.current_step || 'Processing...'}
          </div>
          {progress.iteration !== undefined && progress.max_iterations !== undefined && (
            <div className="text-xs text-slate-500">
              Step {progress.iteration} of {progress.max_iterations}
            </div>
          )}
        </div>
        <ChevronDown
          size={16}
          className={`text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Steps list */}
      {expanded && progress.steps && progress.steps.length > 0 && (
        <div className="border-t border-dark-700 p-3 bg-dark-900 max-h-48 overflow-y-auto">
          <div className="space-y-2">
            {progress.steps.slice(-10).map((step, index) => (
              <div key={index} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full mt-1.5 flex-shrink-0" />
                <div className="text-xs text-slate-400">
                  <span className="text-slate-300">{step.step}</span>
                  {step.details && (
                    <span className="block text-slate-500 mt-0.5">{step.details}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress bar */}
      {progress.status === 'in_progress' && (
        <div className="h-1 bg-dark-700">
          <div className="h-full bg-primary-500 animate-pulse" style={{ width: '100%' }} />
        </div>
      )}

      {/* Error message */}
      {progress.error && (
        <div className="p-3 bg-red-500/10 border-t border-red-500/20 text-sm text-red-400">
          {progress.error}
        </div>
      )}
    </div>
  );
}
