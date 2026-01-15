import { useState, useEffect } from 'react';
import { Image, FileText, Download, RefreshCw, X } from 'lucide-react';
import { getSessionVisualizations, getFileDownloadUrl } from '../services/api';

interface VisualizationsPanelProps {
  sessionId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function VisualizationsPanel({ sessionId, isOpen, onClose }: VisualizationsPanelProps) {
  const [images, setImages] = useState<string[]>([]);
  const [reports, setReports] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedImage, setExpandedImage] = useState<string | null>(null);

  const fetchVisualizations = async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getSessionVisualizations(sessionId);
      setImages(data.images || []);
      setReports(data.reports || []);
    } catch (err) {
      setError('Failed to load visualizations');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && sessionId) {
      fetchVisualizations();
    }
  }, [isOpen, sessionId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-4xl max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
              <Image size={20} className="text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Session Visualizations</h2>
              <p className="text-sm text-slate-400">
                {images.length} images, {reports.length} reports
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchVisualizations}
              disabled={loading}
              className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw size={18} className={`text-slate-400 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
            >
              <X size={18} className="text-slate-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(80vh-80px)]">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw size={24} className="text-primary-400 animate-spin" />
            </div>
          )}

          {error && (
            <div className="text-center py-8 text-red-400">{error}</div>
          )}

          {!loading && !error && images.length === 0 && reports.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 bg-dark-800 rounded-2xl flex items-center justify-center">
                <Image size={32} className="text-slate-600" />
              </div>
              <p className="text-slate-400">No visualizations found</p>
              <p className="text-sm text-slate-500 mt-1">
                Ask Claude to generate some charts or graphs
              </p>
            </div>
          )}

          {/* Images Grid */}
          {images.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <Image size={16} className="text-purple-400" />
                Charts & Graphs ({images.length})
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {images.map((path, idx) => (
                  <div
                    key={idx}
                    className="bg-dark-800 rounded-xl p-3 border border-dark-700 hover:border-purple-500/30 transition-all cursor-pointer group"
                    onClick={() => setExpandedImage(expandedImage === path ? null : path)}
                  >
                    <img
                      src={getFileDownloadUrl(sessionId!, path)}
                      alt={path.split('/').pop()}
                      className="w-full rounded-lg mb-2"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y="50" x="50" text-anchor="middle" fill="%23666">Error</text></svg>';
                      }}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400 truncate flex-1">
                        {path.split('/').pop()}
                      </span>
                      <a
                        href={getFileDownloadUrl(sessionId!, path)}
                        download
                        onClick={(e) => e.stopPropagation()}
                        className="p-1 hover:bg-dark-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Download size={14} className="text-purple-400" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reports List */}
          {reports.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-blue-400" />
                Reports ({reports.length})
              </h3>
              <div className="space-y-2">
                {reports.map((path, idx) => (
                  <a
                    key={idx}
                    href={getFileDownloadUrl(sessionId!, path)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 bg-dark-800 rounded-xl border border-dark-700 hover:border-blue-500/30 transition-all group"
                  >
                    <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                      <FileText size={16} className="text-blue-400" />
                    </div>
                    <span className="text-sm text-slate-300 flex-1 truncate">
                      {path.split('/').pop()}
                    </span>
                    <Download size={14} className="text-slate-500 group-hover:text-blue-400 transition-colors" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Expanded Image Modal */}
        {expandedImage && (
          <div
            className="fixed inset-0 z-60 flex items-center justify-center bg-black/80 p-8"
            onClick={() => setExpandedImage(null)}
          >
            <img
              src={getFileDownloadUrl(sessionId!, expandedImage)}
              alt={expandedImage}
              className="max-w-full max-h-full rounded-xl shadow-2xl"
            />
          </div>
        )}
      </div>
    </div>
  );
}
