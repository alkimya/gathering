/**
 * Enhanced Markdown Preview with Magic Features
 *
 * Phase 8.3 - Advanced Editor Mode for Markdown
 *
 * Features:
 * - Mermaid diagrams (flowcharts, sequence, gantt, etc.)
 * - LaTeX math equations (inline $...$ and block $$...$$)
 * - Syntax highlighted code blocks
 * - Interactive table of contents
 * - Copy code buttons
 * - Dark theme optimized
 */

import { useEffect, useState, useRef, forwardRef, useImperativeHandle, useCallback } from 'react';
import { marked } from 'marked';
import mermaid from 'mermaid';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import {
  Loader2,
  AlertCircle,
  List,
  Check,
  Sparkles,
  GitBranch,
  Calculator,
  RefreshCw,
} from 'lucide-react';

interface MarkdownEnhancedProps {
  content: string;
  loading?: boolean;
  error?: string | null;
}

export interface MarkdownEnhancedHandle {
  getScrollContainer: () => HTMLDivElement | null;
  refresh: () => void;
}

interface TOCItem {
  id: string;
  text: string;
  level: number;
}

// Initialize Mermaid with dark theme
// Note: suppressErrors prevents error popups on invalid syntax
mermaid.initialize({
  startOnLoad: false,
  suppressErrorRendering: true,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#8b5cf6',
    primaryTextColor: '#f4f4f5',
    primaryBorderColor: '#6d28d9',
    lineColor: '#a78bfa',
    secondaryColor: '#1e1b4b',
    tertiaryColor: '#312e81',
    background: '#18181b',
    mainBkg: '#27272a',
    secondBkg: '#3f3f46',
    border1: '#52525b',
    border2: '#71717a',
    arrowheadColor: '#a78bfa',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '14px',
    textColor: '#f4f4f5',
    nodeTextColor: '#f4f4f5',
  },
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
  },
  sequence: {
    diagramMarginX: 50,
    diagramMarginY: 10,
    actorMargin: 50,
    width: 150,
    height: 65,
    boxMargin: 10,
    boxTextMargin: 5,
    noteMargin: 10,
    messageMargin: 35,
  },
});

// Custom renderer for marked v17+
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const createCustomRenderer = (): any => {
  return {
    // Custom heading with anchor links
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    heading(this: any, { tokens, depth }: { tokens: any[]; depth: number }) {
      const text = tokens.map((t: any) => 'text' in t ? t.text : '').join('');
      const slug = text.toLowerCase().replace(/[^\w]+/g, '-');
      const parsed = this.parser?.parseInline(tokens) || text;
      return `
        <h${depth} id="${slug}" class="group flex items-center gap-2 cursor-pointer hover:text-purple-400 transition-colors">
          <a href="#${slug}" class="opacity-0 group-hover:opacity-100 transition-opacity text-purple-500">#</a>
          ${parsed}
        </h${depth}>
      `;
    },

    // Custom code blocks with copy button placeholder
    code({ text, lang }: { text: string; lang?: string }) {
      const language = lang || 'text';
      const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');

      // Mermaid diagrams
      if (language === 'mermaid') {
        return `<div class="mermaid-container" data-mermaid="${encodeURIComponent(text)}"></div>`;
      }

      return `
        <div class="code-block-wrapper group relative">
          <div class="code-block-header flex items-center justify-between px-4 py-2 bg-zinc-800/50 rounded-t-lg border-b border-white/5">
            <span class="text-xs text-zinc-500 font-mono">${language}</span>
            <button class="copy-code-btn opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-white/10 rounded" data-code="${encodeURIComponent(text)}">
              <svg class="w-4 h-4 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
          </div>
          <pre class="!mt-0 !rounded-t-none"><code class="language-${language}">${escaped}</code></pre>
        </div>
      `;
    },

    // Custom blockquote with callout support
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    blockquote(this: any, { tokens }: { tokens: any[] }) {
      const content = this.parser?.parse(tokens) || '';
      // Check for callout types
      const calloutMatch = content.match(/^\s*<p>\s*\[!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]/i);
      if (calloutMatch) {
        const type = calloutMatch[1].toUpperCase();
        const cleanContent = content.replace(/^\s*<p>\s*\[!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]\s*/i, '<p>');
        const colors: Record<string, string> = {
          NOTE: 'border-blue-500 bg-blue-500/10',
          TIP: 'border-green-500 bg-green-500/10',
          WARNING: 'border-yellow-500 bg-yellow-500/10',
          CAUTION: 'border-red-500 bg-red-500/10',
          IMPORTANT: 'border-purple-500 bg-purple-500/10',
        };
        const icons: Record<string, string> = {
          NOTE: '📝',
          TIP: '💡',
          WARNING: '⚠️',
          CAUTION: '🚨',
          IMPORTANT: '⭐',
        };
        return `
          <div class="callout ${colors[type]} border-l-4 p-4 my-4 rounded-r-lg">
            <div class="flex items-center gap-2 font-semibold mb-2">
              <span>${icons[type]}</span>
              <span>${type}</span>
            </div>
            ${cleanContent}
          </div>
        `;
      }
      return `<blockquote>${content}</blockquote>`;
    },

    // Custom table with better styling
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    table(this: any, { header, rows }: { header: any[]; rows: any[][] }) {
      const headerHtml = header.map((cell: any) => {
        const cellContent = this.parser?.parseInline(cell.tokens) || cell.text;
        return `<th style="text-align: ${cell.align || 'left'}">${cellContent}</th>`;
      }).join('');

      const bodyHtml = rows.map((row: any[]) => {
        const cells = row.map((cell: any) => {
          const cellContent = this.parser?.parseInline(cell.tokens) || cell.text;
          return `<td style="text-align: ${cell.align || 'left'}">${cellContent}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
      }).join('');

      return `
        <div class="table-wrapper overflow-x-auto my-4">
          <table class="w-full border-collapse">
            <thead class="bg-zinc-800/50"><tr>${headerHtml}</tr></thead>
            <tbody>${bodyHtml}</tbody>
          </table>
        </div>
      `;
    },

    // Custom checkbox for task lists
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    listitem(this: any, { tokens, task, checked }: { tokens: any[]; task: boolean; checked: boolean }) {
      const content = this.parser?.parse(tokens) || '';
      if (task) {
        return `
          <li class="task-item flex items-start gap-2">
            <input type="checkbox" ${checked ? 'checked' : ''} disabled class="mt-1.5 accent-purple-500" />
            <span class="${checked ? 'line-through text-zinc-500' : ''}">${content}</span>
          </li>
        `;
      }
      return `<li>${content}</li>`;
    },
  };
};

// Process LaTeX math expressions BEFORE marked (to avoid HTML entity encoding)
const extractAndProcessLatex = (content: string): { processed: string; placeholders: Map<string, string> } => {
  const placeholders = new Map<string, string>();
  let counter = 0;

  // Block math: $$...$$ (process first to avoid conflicts)
  let processed = content.replace(/\$\$([\s\S]*?)\$\$/g, (_, math) => {
    const placeholder = `%%LATEX_BLOCK_${counter++}%%`;
    try {
      placeholders.set(placeholder, `<div class="math-block my-4 overflow-x-auto">${katex.renderToString(math.trim(), {
        displayMode: true,
        throwOnError: false,
        trust: true,
      })}</div>`);
    } catch (e) {
      placeholders.set(placeholder, `<div class="math-error text-red-400 p-2 bg-red-500/10 rounded">LaTeX error: ${math}</div>`);
    }
    return placeholder;
  });

  // Inline math: $...$ (avoid matching $$ or empty)
  processed = processed.replace(/\$([^\$\n]+?)\$/g, (_, math) => {
    const placeholder = `%%LATEX_INLINE_${counter++}%%`;
    try {
      placeholders.set(placeholder, katex.renderToString(math.trim(), {
        displayMode: false,
        throwOnError: false,
        trust: true,
      }));
    } catch (e) {
      placeholders.set(placeholder, `<span class="math-error text-red-400">${math}</span>`);
    }
    return placeholder;
  });

  return { processed, placeholders };
};

// Restore LaTeX placeholders after marked processing
const restoreLatexPlaceholders = (html: string, placeholders: Map<string, string>): string => {
  placeholders.forEach((value, key) => {
    html = html.replace(key, value);
  });
  return html;
};

// Extract table of contents
const extractTOC = (content: string): TOCItem[] => {
  const toc: TOCItem[] = [];
  const headingRegex = /^(#{1,6})\s+(.+)$/gm;
  let match;

  while ((match = headingRegex.exec(content)) !== null) {
    const level = match[1].length;
    const text = match[2].replace(/\*\*|__|\*|_|`/g, ''); // Remove markdown formatting
    const id = text.toLowerCase().replace(/[^\w]+/g, '-');
    toc.push({ id, text, level });
  }

  return toc;
};

export const MarkdownEnhanced = forwardRef<MarkdownEnhancedHandle, MarkdownEnhancedProps>(
  ({ content, loading, error }, ref) => {
    const [html, setHtml] = useState('');
    const [toc, setToc] = useState<TOCItem[]>([]);
    const [showTOC, setShowTOC] = useState(true);
    const [copiedCode, setCopiedCode] = useState<string | null>(null);
    const [mermaidCount, setMermaidCount] = useState(0);
    const [mathCount, setMathCount] = useState(0);
    const [mermaidRendered, setMermaidRendered] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const lastContentRef = useRef<string>('');

    // Simple refresh trigger
    const triggerRefresh = useCallback(() => {
      lastContentRef.current = '';
      setMermaidRendered(false);
      setRefreshKey(k => k + 1);
    }, []);

    useImperativeHandle(ref, () => ({
      getScrollContainer: () => scrollContainerRef.current,
      refresh: triggerRefresh,
    }), [triggerRefresh]);


    const setupCopyButtons = useCallback(() => {
      if (!contentRef.current) return;

      const copyButtons = contentRef.current.querySelectorAll('.copy-code-btn');
      copyButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const button = e.currentTarget as HTMLElement;
          const code = decodeURIComponent(button.dataset.code || '');

          try {
            await navigator.clipboard.writeText(code);
            setCopiedCode(code);
            setTimeout(() => setCopiedCode(null), 2000);
          } catch (err) {
            console.error('Failed to copy:', err);
          }
        });
      });
    }, []);

    // Render markdown content - only when content actually changes or refresh triggered
    useEffect(() => {
      if (!content) return;

      // Skip if content hasn't changed (prevents wiping Mermaid SVGs)
      // refreshKey change will force re-render because lastContentRef was cleared
      if (content === lastContentRef.current) {
        return;
      }
      lastContentRef.current = content;

      // Count math expressions
      const mathMatches = (content.match(/\$\$[\s\S]*?\$\$|\$[^\$\n]+?\$/g) || []).length;
      setMathCount(mathMatches);

      // Process LaTeX BEFORE marked to avoid HTML entity encoding issues
      const { processed: contentWithPlaceholders, placeholders } = extractAndProcessLatex(content);

      // Configure marked
      marked.setOptions({
        gfm: true,
        breaks: true,
      });
      marked.use({ renderer: createCustomRenderer() });

      // Render markdown
      let rendered = marked(contentWithPlaceholders) as string;

      // Restore LaTeX after marked processing
      rendered = restoreLatexPlaceholders(rendered, placeholders);

      // Extract TOC
      setToc(extractTOC(content));

      // Now render Mermaid diagrams BEFORE setting HTML
      // This prevents React from overwriting the SVGs on re-render
      const renderMermaidInHtml = async () => {
        // Find all mermaid containers and render them
        const mermaidRegex = /<div class="mermaid-container" data-mermaid="([^"]+)"><\/div>/g;
        let match;
        let processedHtml = rendered;
        let count = 0;

        // Re-initialize mermaid
        mermaid.initialize({
          startOnLoad: false,
          suppressErrorRendering: true,
          theme: 'dark',
          themeVariables: {
            primaryColor: '#8b5cf6',
            primaryTextColor: '#f4f4f5',
            primaryBorderColor: '#6d28d9',
            lineColor: '#a78bfa',
            secondaryColor: '#1e1b4b',
            tertiaryColor: '#312e81',
            background: '#18181b',
            mainBkg: '#27272a',
            secondBkg: '#3f3f46',
            border1: '#52525b',
            border2: '#71717a',
            arrowheadColor: '#a78bfa',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '14px',
            textColor: '#f4f4f5',
            nodeTextColor: '#f4f4f5',
          },
        });

        // Collect all matches first
        const matches: { full: string; code: string }[] = [];
        while ((match = mermaidRegex.exec(rendered)) !== null) {
          matches.push({ full: match[0], code: decodeURIComponent(match[1]) });
        }

        // Render each mermaid diagram
        for (let i = 0; i < matches.length; i++) {
          const { full, code } = matches[i];
          try {
            const id = `mermaid-${Date.now()}-${i}`;
            const { svg } = await mermaid.render(id, code);
            const replacement = `
              <div class="mermaid-diagram bg-zinc-900/50 p-4 rounded-lg border border-white/5 my-4 overflow-x-auto">
                <div class="flex items-center gap-2 mb-3 text-xs text-zinc-500">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 3v18M3 12h18M7 7l5 5-5 5M17 7l-5 5 5 5"/>
                  </svg>
                  Mermaid Diagram
                </div>
                ${svg}
              </div>
            `;
            processedHtml = processedHtml.replace(full, replacement);
            count++;
          } catch (e: unknown) {
            const errorMsg = e instanceof Error ? e.message : 'Unknown error';
            console.error('Mermaid render error:', errorMsg);
            const replacement = `
              <div class="mermaid-error p-4 bg-red-500/10 border border-red-500/30 rounded-lg my-4">
                <div class="flex items-center gap-2 text-red-400 mb-2">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                  Mermaid Error: ${errorMsg}
                </div>
                <pre class="text-xs text-red-300 overflow-x-auto">${code}</pre>
              </div>
            `;
            processedHtml = processedHtml.replace(full, replacement);
          }
        }

        setMermaidCount(count);
        setHtml(processedHtml);
        setMermaidRendered(true);
      };

      renderMermaidInHtml();
    }, [content, refreshKey]);

    // Setup anchor link click handlers to prevent default navigation
    const setupAnchorLinks = useCallback(() => {
      if (!contentRef.current) return;

      const anchorLinks = contentRef.current.querySelectorAll('a[href^="#"]');
      anchorLinks.forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const href = (link as HTMLAnchorElement).getAttribute('href');
          if (href && href.startsWith('#')) {
            const targetId = href.slice(1);
            const element = document.getElementById(targetId);
            if (element) {
              element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }
        });
      });
    }, []);

    // Setup copy buttons and anchor links after HTML is rendered
    useEffect(() => {
      if (html && mermaidRendered) {
        // Use requestAnimationFrame to ensure DOM is fully rendered before processing
        requestAnimationFrame(() => {
          setupCopyButtons();
          setupAnchorLinks();
        });
      }
    }, [html, mermaidRendered, setupCopyButtons, setupAnchorLinks]);

    const scrollToHeading = (id: string) => {
      const element = document.getElementById(id);
      if (element && scrollContainerRef.current) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center h-full bg-[#1e1e1e]">
          <Loader2 className="w-12 h-12 text-purple-500 animate-spin mb-4" />
          <p className="text-zinc-400">Rendering magic...</p>
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
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-white font-medium">Enhanced Preview</span>

            {/* Feature badges */}
            <div className="flex items-center gap-2 ml-4">
              {mermaidCount > 0 && (
                <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded-full">
                  <GitBranch className="w-3 h-3" />
                  {mermaidCount} diagram{mermaidCount > 1 ? 's' : ''}
                </span>
              )}
              {mathCount > 0 && (
                <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">
                  <Calculator className="w-3 h-3" />
                  {mathCount} math
                </span>
              )}
              {toc.length > 0 && (
                <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded-full">
                  <List className="w-3 h-3" />
                  {toc.length} headings
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={triggerRefresh}
              className="p-1.5 hover:bg-white/10 rounded transition-colors"
              title="Refresh preview"
            >
              <RefreshCw className="w-4 h-4 text-zinc-400" />
            </button>
            {toc.length > 0 && (
              <button
                onClick={() => setShowTOC(!showTOC)}
                className={`p-1.5 rounded transition-colors ${
                  showTOC ? 'bg-purple-500/20 text-purple-400' : 'hover:bg-white/10 text-zinc-400'
                }`}
                title="Toggle table of contents"
              >
                <List className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Table of Contents Sidebar */}
          {showTOC && toc.length > 0 && (
            <div className="w-56 border-r border-white/5 bg-[#1a1a1a] overflow-y-auto custom-scrollbar">
              <div className="p-3">
                <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Contents</div>
                <nav className="space-y-1">
                  {toc.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => scrollToHeading(item.id)}
                      className={`w-full text-left text-sm text-zinc-400 hover:text-purple-400 hover:bg-white/5 rounded px-2 py-1 transition-colors truncate`}
                      style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                    >
                      {item.text}
                    </button>
                  ))}
                </nav>
              </div>
            </div>
          )}

          {/* Preview content */}
          <div ref={scrollContainerRef} className="flex-1 overflow-y-auto custom-scrollbar">
            <div
              ref={contentRef}
              className="markdown-enhanced prose prose-invert max-w-none p-6"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        </div>

        {/* Copy notification */}
        {copiedCode && (
          <div className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-2 bg-green-500/20 border border-green-500/30 rounded-lg text-green-400 text-sm animate-fade-in">
            <Check className="w-4 h-4" />
            Copied to clipboard!
          </div>
        )}

        {/* Styles */}
        <style>{`
          .markdown-enhanced {
            color: #e4e4e7;
          }

          .markdown-enhanced h1,
          .markdown-enhanced h2,
          .markdown-enhanced h3,
          .markdown-enhanced h4,
          .markdown-enhanced h5,
          .markdown-enhanced h6 {
            color: #f4f4f5;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 0.5rem;
            margin-top: 1.5rem;
          }

          .markdown-enhanced a {
            color: #a78bfa;
          }

          .markdown-enhanced a:hover {
            color: #c4b5fd;
          }

          .markdown-enhanced code:not(pre code) {
            background: rgba(139, 92, 246, 0.2);
            color: #c4b5fd;
            padding: 0.2em 0.4em;
            border-radius: 4px;
            font-size: 0.9em;
          }

          .markdown-enhanced pre {
            background: #18181b;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 0 0 8px 8px;
          }

          .markdown-enhanced blockquote {
            border-left: 4px solid #8b5cf6;
            background: rgba(139, 92, 246, 0.1);
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
          }

          .markdown-enhanced table {
            border: 1px solid rgba(255,255,255,0.1);
          }

          .markdown-enhanced th,
          .markdown-enhanced td {
            border: 1px solid rgba(255,255,255,0.1);
            padding: 0.75rem 1rem;
          }

          .markdown-enhanced th {
            background: rgba(39, 39, 42, 0.5);
            font-weight: 600;
          }

          .markdown-enhanced tr:hover {
            background: rgba(255,255,255,0.02);
          }

          .markdown-enhanced hr {
            border-color: rgba(255,255,255,0.1);
          }

          .markdown-enhanced img {
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
          }

          .markdown-enhanced .task-item {
            list-style: none;
            margin-left: -1.5rem;
          }

          .mermaid-diagram svg {
            max-width: 100%;
            height: auto;
          }

          .math-block {
            text-align: center;
          }

          .math-block .katex-display {
            margin: 0;
          }

          @keyframes fade-in {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }

          .animate-fade-in {
            animation: fade-in 0.2s ease-out;
          }
        `}</style>
      </div>
    );
  }
);
