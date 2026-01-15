import { Loader2, CheckCircle, AlertCircle, ChevronDown, Activity } from 'lucide-react';
import type { ProgressData } from '../types';
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
        return (
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
            <CheckCircle className="text-emerald-400" size={18} />
          </div>
        );
      case 'error':
        return (
          <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center">
            <AlertCircle className="text-red-400" size={18} />
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
            <Loader2 className="text-primary-400 animate-spin" size={18} />
          </div>
        );
    }
  };

  const getStatusColor = () => {
    switch (progress.status) {
      case 'completed':
        return 'border-emerald-500/30';
      case 'error':
        return 'border-red-500/30';
      default:
        return 'border-primary-500/30';
    }
  };

  return (
    <div className={`bg-dark-800/50 backdrop-blur-sm border ${getStatusColor()} rounded-2xl mx-4 mb-4 overflow-hidden shadow-lg`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 p-4 hover:bg-dark-700/30 transition-all duration-200"
      >
        {getStatusIcon()}
        <div className="flex-1 text-left">
          <div className="text-sm font-semibold text-slate-200">
            {progress.current_step || 'Processing...'}
          </div>
          {progress.iteration !== undefined && progress.max_iterations !== undefined && (
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
              <Activity size={12} />
              Step {progress.iteration} of {progress.max_iterations}
            </div>
          )}
        </div>
        <ChevronDown
          size={18}
          className={`text-slate-500 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Steps list */}
      {expanded && progress.steps && progress.steps.length > 0 && (
        <div className="border-t border-dark-700/50 p-4 bg-dark-900/50 max-h-48 overflow-y-auto">
          <div className="space-y-3">
            {progress.steps.slice(-10).map((step, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className="w-2 h-2 bg-primary-400 rounded-full mt-1.5 flex-shrink-0 shadow-sm shadow-primary-500/30" />
                <div className="text-sm">
                  <span className="text-slate-300">{step.step}</span>
                  {step.details && (
                    <span className="block text-slate-500 mt-0.5 text-xs">{step.details}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress bar */}
      {progress.status === 'in_progress' && (
        <div className="h-1 bg-dark-700/50">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-emerald-500"
            style={{
              width: '100%',
              animation: 'pulse 2s ease-in-out infinite'
            }}
          />
        </div>
      )}

      {/* Error message */}
      {progress.error && (
        <div className="p-4 bg-red-500/10 border-t border-red-500/20 flex items-start gap-3">
          <div className="w-6 h-6 rounded-lg bg-red-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertCircle className="text-red-400" size={14} />
          </div>
          <span className="text-sm text-red-400">{progress.error}</span>
        </div>
      )}
    </div>
  );
}
