/**
 * Python Runner Component
 * Execute Python code and display output
 */

import { useState } from 'react';
import { Play, Loader2, Terminal as TerminalIcon, Trash2, Copy, Check } from 'lucide-react';
import api from '../../services/api';

interface PythonRunnerProps {
  projectId: number;
  filePath: string | null;
  content: string;
}

interface ExecutionResult {
  stdout: string;
  stderr: string;
  exit_code: number;
  execution_time: number;
}

export function PythonRunner({ projectId, filePath, content }: PythonRunnerProps) {
  const [output, setOutput] = useState<ExecutionResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleRun = async () => {
    try {
      setRunning(true);
      setError(null);

      const response = await api.post(`/workspace/${projectId}/run-python`, {
        code: content,
        file_path: filePath || 'untitled.py',
      });

      setOutput(response.data as ExecutionResult);
    } catch (err: any) {
      console.error('Failed to run Python code:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to execute');
    } finally {
      setRunning(false);
    }
  };

  const handleClear = () => {
    setOutput(null);
    setError(null);
  };

  const handleCopy = async () => {
    if (output) {
      const text = output.stdout + (output.stderr ? '\n' + output.stderr : '');
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 bg-[#252526] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TerminalIcon className="w-4 h-4 text-green-400" />
          <span className="text-sm text-white font-medium">Python Output</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRun}
            disabled={running || !content}
            className="flex items-center gap-2 px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-300 text-sm rounded-lg border border-green-500/30 transition-all disabled:opacity-50"
          >
            {running ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-3 h-3" />
                Run (Shift+Enter)
              </>
            )}
          </button>

          {output && (
            <>
              <button
                onClick={handleCopy}
                className="p-1.5 hover:bg-white/10 rounded transition-colors text-zinc-400 hover:text-white"
                title="Copy Output"
              >
                {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
              </button>
              <button
                onClick={handleClear}
                className="p-1.5 hover:bg-white/10 rounded transition-colors text-zinc-400 hover:text-white"
                title="Clear Output"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Output area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 font-mono text-sm">
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400 font-semibold mb-1">Error:</p>
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {output && (
          <div className="space-y-4">
            {/* Execution info */}
            <div className="flex items-center gap-4 text-xs text-zinc-500">
              <span>Exit Code: <span className={output.exit_code === 0 ? 'text-green-400' : 'text-red-400'}>{output.exit_code}</span></span>
              <span>Time: <span className="text-cyan-400">{output.execution_time.toFixed(3)}s</span></span>
            </div>

            {/* Stdout */}
            {output.stdout && (
              <div>
                <p className="text-green-400 text-xs font-semibold mb-2">Standard Output:</p>
                <pre className="text-zinc-300 whitespace-pre-wrap break-words">{output.stdout}</pre>
              </div>
            )}

            {/* Stderr */}
            {output.stderr && (
              <div>
                <p className="text-red-400 text-xs font-semibold mb-2">Standard Error:</p>
                <pre className="text-red-300 whitespace-pre-wrap break-words">{output.stderr}</pre>
              </div>
            )}

            {!output.stdout && !output.stderr && output.exit_code === 0 && (
              <p className="text-zinc-500 italic">No output (execution successful)</p>
            )}
          </div>
        )}

        {!output && !error && (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500">
            <Play className="w-12 h-12 mb-3 opacity-50" />
            <p>Click "Run" or press Shift+Enter to execute Python code</p>
            <p className="text-xs mt-2">Code will run in a sandboxed environment</p>
          </div>
        )}
      </div>
    </div>
  );
}
