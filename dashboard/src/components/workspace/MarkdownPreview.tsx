/**
 * Markdown Preview Component
 * Renders markdown files with GitHub-flavored styling
 */

import { useEffect, useState, useRef, forwardRef, useImperativeHandle } from 'react';
import { marked } from 'marked';
import { Eye, Loader2, AlertCircle } from 'lucide-react';

interface MarkdownPreviewProps {
  content: string;
  loading?: boolean;
  error?: string | null;
}

export interface MarkdownPreviewHandle {
  getScrollContainer: () => HTMLDivElement | null;
}

export const MarkdownPreview = forwardRef<MarkdownPreviewHandle, MarkdownPreviewProps>(
  ({ content, loading, error }, ref) => {
    const [html, setHtml] = useState('');
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    useImperativeHandle(ref, () => ({
      getScrollContainer: () => scrollContainerRef.current,
    }));

    useEffect(() => {
      if (content) {
        // Configure marked for GitHub-flavored markdown
        marked.setOptions({
          gfm: true,
          breaks: true,
        });

        const rendered = marked(content);
        setHtml(rendered as string);
      }
    }, [content]);

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
        <div className="px-4 py-3 border-b border-white/5 bg-[#252526] flex items-center gap-3">
          <Eye className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-white font-medium">Markdown Preview</span>
        </div>

        {/* Preview content */}
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto custom-scrollbar">
          <div
            className="markdown-preview prose prose-invert max-w-none p-6"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      </div>
    );
  }
);
