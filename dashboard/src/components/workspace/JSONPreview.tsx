/**
 * JSON Preview Component - Web3 Dark Theme
 * Pretty-prints JSON with syntax highlighting
 */

import { useState, useEffect } from 'react';
import { Copy, Check, Minimize2, Maximize2 } from 'lucide-react';

interface JSONPreviewProps {
  content: string;
}

export function JSONPreview({ content }: JSONPreviewProps) {
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [formattedJSON, setFormattedJSON] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const parsed = JSON.parse(content);
      const formatted = JSON.stringify(parsed, null, 2);
      setFormattedJSON(formatted);
      setError(null);
    } catch (err) {
      setError('Invalid JSON');
      setFormattedJSON(content);
    }
  }, [content]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJSON);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const syntaxHighlight = (json: string) => {
    return json
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
        let cls = 'text-amber-400'; // numbers
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'text-purple-400'; // keys
          } else {
            cls = 'text-green-400'; // strings
          }
        } else if (/true|false/.test(match)) {
          cls = 'text-cyan-400'; // booleans
        } else if (/null/.test(match)) {
          cls = 'text-red-400'; // null
        }
        return `<span class="${cls}">${match}</span>`;
      });
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-purple-900/10 to-slate-900">
      {/* Toolbar */}
      <div className="glass-card border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="px-3 py-1 bg-purple-500/10 text-purple-400 text-xs font-medium rounded-lg border border-purple-500/20">
            JSON
          </div>
          {error && (
            <div className="px-3 py-1 bg-red-500/10 text-red-400 text-xs font-medium rounded-lg border border-red-500/20">
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title={collapsed ? "Expand All" : "Collapse All"}
          >
            {collapsed ? (
              <Maximize2 className="w-4 h-4 text-zinc-400 group-hover:text-purple-400" />
            ) : (
              <Minimize2 className="w-4 h-4 text-zinc-400 group-hover:text-purple-400" />
            )}
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-lg transition-colors group"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-400" />
                <span className="text-xs text-green-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-zinc-400 group-hover:text-purple-400" />
                <span className="text-xs text-zinc-400 group-hover:text-purple-400">Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* JSON Display */}
      <div className="flex-1 overflow-auto p-6">
        <pre className="text-sm font-mono leading-relaxed">
          <code
            dangerouslySetInnerHTML={{
              __html: syntaxHighlight(formattedJSON),
            }}
          />
        </pre>
      </div>
    </div>
  );
}
