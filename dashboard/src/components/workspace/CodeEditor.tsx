/**
 * Code Editor Component - Web3 Dark Theme with Monaco
 */

import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import Editor from '@monaco-editor/react';
import { Save, Loader2, FileCode, AlertCircle } from 'lucide-react';
import api from '../../services/api';

interface CodeEditorProps {
  projectId: number;
  onContentChange?: (content: string) => void;
  filePath: string | null;
}

export interface CodeEditorHandle {
  getEditor: () => any;
}

export const CodeEditor = forwardRef<CodeEditorHandle, CodeEditorProps>(
  ({ projectId, filePath, onContentChange }, ref) => {
    const [fileContent, setFileContent] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasChanges, setHasChanges] = useState(false);
    const [saving, setSaving] = useState(false);
    const editorRef = useRef<any>(null);
    const [currentValue, setCurrentValue] = useState('');

    useImperativeHandle(ref, () => ({
      getEditor: () => editorRef.current,
    }));

  useEffect(() => {
    if (filePath) {
      loadFile(filePath);
    } else {
      setFileContent(null);
      setCurrentValue('');
    }
  }, [filePath, projectId]);

  const loadFile = async (path: string) => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/file`, {
        params: { path },
      });

      const content = (response.data as any)?.content || '';
      setFileContent(response.data as any);
      setCurrentValue(content);
      setHasChanges(false);

      // Notify parent of initial content for preview
      if (onContentChange) {
        onContentChange(content);
      }
    } catch (err: any) {
      console.error('Failed to load file:', err);
      setError(err.message || 'Failed to load file');
    } finally {
      setLoading(false);
    }
  };

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;

    // Ctrl+S to save
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
      () => handleSave()
    );
  };

  const handleEditorChange = (value: string | undefined) => {
    setCurrentValue(value || '');
    setHasChanges(value !== fileContent?.content);
    if (onContentChange) {
      onContentChange(value || '');
    }
  };

  const handleSave = async () => {
    if (!filePath || !hasChanges) return;

    try {
      setSaving(true);
      await api.put(
        `/workspace/${projectId}/file`,
        { content: currentValue },
        { params: { path: filePath } }
      );

      setFileContent({ ...fileContent, content: currentValue });
      setHasChanges(false);
    } catch (err: any) {
      console.error('Failed to save file:', err);
      setError(err.message || 'Failed to save file');
    } finally {
      setSaving(false);
    }
  };

  const getLanguage = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      ts: 'typescript',
      tsx: 'typescript',
      js: 'javascript',
      jsx: 'javascript',
      py: 'python',
      json: 'json',
      md: 'markdown',
      css: 'css',
      html: 'html',
      sql: 'sql',
      sh: 'shell',
    };
    return langMap[ext || ''] || 'plaintext';
  };

  if (!filePath) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#1e1e1e]">
        <FileCode className="w-16 h-16 text-zinc-600 mb-4" />
        <p className="text-zinc-500">Select a file to view</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#1e1e1e]">
        <Loader2 className="w-12 h-12 text-purple-500 animate-spin mb-4" />
        <p className="text-zinc-400">Loading {filePath}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#1e1e1e] p-8">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <p className="text-red-400 text-center mb-4">{error}</p>
        <button
          onClick={() => loadFile(filePath)}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 bg-[#252526] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileCode className="w-4 h-4 text-cyan-400" />
          <span className="text-sm text-white font-medium">{filePath?.split('/').pop()}</span>
          {hasChanges && (
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          )}
        </div>

        {hasChanges && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 text-sm rounded-lg border border-purple-500/30 transition-all disabled:opacity-50"
          >
            {saving ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-3 h-3" />
                Save (Ctrl+S)
              </>
            )}
          </button>
        )}
      </div>

      {/* Monaco Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          language={getLanguage(filePath)}
          value={currentValue}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            minimap: { enabled: (fileContent?.lines || 0) > 100 },
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            lineNumbers: 'on',
            rulers: [80, 120],
            wordWrap: 'on',
            smoothScrolling: true,
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            renderWhitespace: 'selection',
            bracketPairColorization: { enabled: true },
            guides: {
              bracketPairs: true,
              indentation: true,
            },
          }}
        />
      </div>

      {/* Status bar */}
      <div className="px-4 py-2 border-t border-white/5 bg-[#252526] flex items-center justify-between text-xs text-zinc-500">
        <div className="flex items-center gap-4">
          <span>{getLanguage(filePath)}</span>
          <span>Lines: {fileContent?.lines || 0}</span>
          {fileContent?.size_bytes && (
            <span>Size: {(fileContent.size_bytes / 1024).toFixed(1)} KB</span>
          )}
        </div>
        {hasChanges && <span className="text-amber-400">● Modified</span>}
      </div>
    </div>
  );
});
