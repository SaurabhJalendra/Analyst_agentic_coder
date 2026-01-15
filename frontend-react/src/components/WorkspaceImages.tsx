import { useState, useEffect } from 'react';
import { Image, ChevronDown, ChevronUp, Download, RefreshCw } from 'lucide-react';
import { getSessionVisualizations, getFileDownloadUrl } from '../services/api';

interface WorkspaceImagesProps {
  sessionId: string | null;
}

export function WorkspaceImages({ sessionId }: WorkspaceImagesProps) {
  const [images, setImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const fetchImages = async () => {
    if (!sessionId) {
      setImages([]);
      return;
    }

    setLoading(true);
    try {
      const data = await getSessionVisualizations(sessionId);
      setImages(data.images || []);
    } catch (err) {
      console.error('Failed to fetch visualizations:', err);
      setImages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImages();
  }, [sessionId]);

  // Don't show if no session or no images
  if (!sessionId || images.length === 0) {
    return null;
  }

  return (
    <>
      <div className="border-t border-dark-700/50 bg-dark-900/50">
        {/* Header */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-dark-800/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Image size={16} className="text-purple-400" />
            </div>
            <span className="text-sm font-medium text-slate-300">
              Generated Visualizations ({images.length})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                fetchImages();
              }}
              className="p-1.5 hover:bg-dark-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw size={14} className={`text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            </button>
            {expanded ? (
              <ChevronUp size={18} className="text-slate-500" />
            ) : (
              <ChevronDown size={18} className="text-slate-500" />
            )}
          </div>
        </button>

        {/* Images Grid */}
        {expanded && (
          <div className="px-4 pb-4">
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {images.slice(0, 12).map((path, idx) => (
                <div
                  key={idx}
                  className="relative group cursor-pointer"
                  onClick={() => setSelectedImage(path)}
                >
                  <div className="aspect-square bg-dark-800 rounded-xl overflow-hidden border border-dark-700 hover:border-purple-500/50 transition-all">
                    <img
                      src={getFileDownloadUrl(sessionId, path)}
                      alt={path.split('/').pop()}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl flex items-center justify-center">
                    <span className="text-xs text-white text-center px-2 truncate">
                      {path.split('/').pop()}
                    </span>
                  </div>
                </div>
              ))}
              {images.length > 12 && (
                <div className="aspect-square bg-dark-800 rounded-xl border border-dark-700 flex items-center justify-center">
                  <span className="text-sm text-slate-400">+{images.length - 12} more</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Lightbox Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-8"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-5xl max-h-full">
            <img
              src={getFileDownloadUrl(sessionId, selectedImage)}
              alt={selectedImage}
              className="max-w-full max-h-[80vh] rounded-xl shadow-2xl"
            />
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-4 bg-dark-900/90 px-4 py-2 rounded-xl">
              <span className="text-sm text-slate-300">{selectedImage.split('/').pop()}</span>
              <a
                href={getFileDownloadUrl(sessionId, selectedImage)}
                download
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1.5 text-sm text-purple-400 hover:text-purple-300"
              >
                <Download size={14} />
                Download
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
