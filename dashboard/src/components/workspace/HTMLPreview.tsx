/**
 * HTML Preview Component
 * Renders HTML files in an iframe with security sandboxing
 */

import { useEffect, useState, useRef } from 'react';
import { Eye, Loader2, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react';

interface HTMLPreviewProps {
  content: string;
  loading?: boolean;
  error?: string | null;
}

export function HTMLPreview({ content, loading, error }: HTMLPreviewProps) {
  const [key, setKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (content && iframeRef.current) {
      const iframe = iframeRef.current;
      const doc = iframe.contentDocument || iframe.contentWindow?.document;

      if (doc) {
        doc.open();
        doc.write(content);
        doc.close();
      }
    }
  }, [content, key]);

  const handleRefresh = () => {
    setKey(prev => prev + 1);
  };

  const handleOpenInNewTab = () => {
    const blob = new Blob([content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#1e1e1e]">
        <Loader2 className="w-12 h-12 text-purple-500 animate-spin mb-4" />
        <p className="text-zinc-400">Loading preview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#1e1e1e] p-8">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <p className="text-red-400 text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 bg-[#252526] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Eye className="w-4 h-4 text-amber-400" />
          <span className="text-sm text-white font-medium">HTML Preview</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="p-1.5 hover:bg-white/10 rounded transition-colors text-zinc-400 hover:text-white"
            title="Refresh Preview"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleOpenInNewTab}
            className="p-1.5 hover:bg-white/10 rounded transition-colors text-zinc-400 hover:text-white"
            title="Open in New Tab"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Preview iframe */}
      <div className="flex-1 overflow-hidden bg-white">
        <iframe
          key={key}
          ref={iframeRef}
          className="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin allow-forms"
          title="HTML Preview"
        />
      </div>
    </div>
  );
}
