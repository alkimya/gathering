/**
 * Image Preview Component - Web3 Dark Theme
 * Displays images with zoom and pan controls
 */

import { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2, Download, RotateCw } from 'lucide-react';

interface ImagePreviewProps {
  filePath: string;
  projectId: number;
}

export function ImagePreview({ filePath, projectId }: ImagePreviewProps) {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);

  // Use /file/raw endpoint to get binary image data with correct MIME type
  const imageUrl = `/api/workspace/${projectId}/file/raw?path=${encodeURIComponent(filePath)}`;

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 400));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 25));
  const handleRotate = () => setRotation(prev => (prev + 90) % 360);
  const handleReset = () => {
    setZoom(100);
    setRotation(0);
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filePath.split('/').pop() || 'image';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download image:', error);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-purple-900/10 to-slate-900">
      {/* Toolbar */}
      <div className="glass-card border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400">Zoom: {zoom}%</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4 text-zinc-400 group-hover:text-purple-400" />
          </button>

          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4 text-zinc-400 group-hover:text-purple-400" />
          </button>

          <button
            onClick={handleRotate}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title="Rotate"
          >
            <RotateCw className="w-4 h-4 text-zinc-400 group-hover:text-cyan-400" />
          </button>

          <button
            onClick={handleReset}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title="Reset"
          >
            <Maximize2 className="w-4 h-4 text-zinc-400 group-hover:text-amber-400" />
          </button>

          <div className="w-px h-6 bg-white/10 mx-2"></div>

          <button
            onClick={handleDownload}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title="Download"
          >
            <Download className="w-4 h-4 text-zinc-400 group-hover:text-green-400" />
          </button>
        </div>
      </div>

      {/* Image Display */}
      <div className="flex-1 overflow-auto p-8 flex items-center justify-center">
        <div
          className="transition-transform duration-200"
          style={{
            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
          }}
        >
          <img
            src={imageUrl}
            alt={filePath}
            className="max-w-full h-auto rounded-lg shadow-2xl border border-white/10"
            style={{
              imageRendering: zoom > 200 ? 'pixelated' : 'auto',
            }}
          />
        </div>
      </div>

      {/* Image Info */}
      <div className="glass-card border-t border-white/5 px-4 py-2">
        <p className="text-xs text-zinc-500 text-center">
          {filePath.split('/').pop()}
        </p>
      </div>
    </div>
  );
}
