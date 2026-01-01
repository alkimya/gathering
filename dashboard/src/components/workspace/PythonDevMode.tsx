/**
 * Python Dev Mode - Advanced Python Development Panel
 *
 * Phase 8.3 - Advanced Editor Mode for Python
 *
 * Features:
 * - Interactive REPL with history
 * - Run current file
 * - Run tests (pytest)
 * - Code profiler
 * - Variable inspector
 */

import { useState, useRef, useEffect } from 'react';
import {
  Play,
  Loader2,
  Terminal as TerminalIcon,
  TestTube,
  ChevronRight,
  Sparkles,
  Zap,
  FileCode,
  BarChart3,
} from 'lucide-react';
import api from '../../services/api';

interface PythonDevModeProps {
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

interface TestResult {
  name: string;
  status: 'passed' | 'failed' | 'skipped' | 'error';
  duration: number;
  message?: string;
}

interface ProfileResult {
  function: string;
  calls: number;
  total_time: number;
  per_call: number;
  cumulative: number;
}

type TabType = 'run' | 'repl' | 'tests' | 'profile';

export function PythonDevMode({ projectId, filePath, content }: PythonDevModeProps) {
  const [activeTab, setActiveTab] = useState<TabType>('run');

  // Run tab state
  const [runOutput, setRunOutput] = useState<ExecutionResult | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  // REPL tab state
  const [replHistory, setReplHistory] = useState<{ input: string; output: string; error?: boolean }[]>([]);
  const [replInput, setReplInput] = useState('');
  const [replRunning, setReplRunning] = useState(false);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const replInputRef = useRef<HTMLInputElement>(null);
  const replOutputRef = useRef<HTMLDivElement>(null);

  // Tests tab state
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [testRunning, setTestRunning] = useState(false);
  const [testSummary, setTestSummary] = useState<{ passed: number; failed: number; skipped: number; duration: number } | null>(null);
  const [testRawOutput, setTestRawOutput] = useState<string>('');

  // Profile tab state
  const [profileResults, setProfileResults] = useState<ProfileResult[]>([]);
  const [profileRunning, setProfileRunning] = useState(false);
  const [totalProfileTime, setTotalProfileTime] = useState(0);

  // Common state - removed unused copied state

  // Auto-scroll REPL output
  useEffect(() => {
    if (replOutputRef.current) {
      replOutputRef.current.scrollTop = replOutputRef.current.scrollHeight;
    }
  }, [replHistory]);

  // Run Python file
  const handleRun = async () => {
    try {
      setRunning(true);
      setRunError(null);

      const response = await api.post(`/workspace/${projectId}/run-python`, {
        code: content,
        file_path: filePath || 'untitled.py',
      });

      setRunOutput(response.data as ExecutionResult);
    } catch (err: any) {
      console.error('Failed to run Python code:', err);
      setRunError(err.response?.data?.detail || err.message || 'Failed to execute');
    } finally {
      setRunning(false);
    }
  };

  // REPL execute
  const handleReplExecute = async () => {
    if (!replInput.trim() || replRunning) return;

    const input = replInput;
    setReplInput('');
    setReplRunning(true);
    setCommandHistory(prev => [...prev, input]);
    setHistoryIndex(-1);

    try {
      const response = await api.post(`/workspace/${projectId}/run-python`, {
        code: input,
        file_path: '_repl_.py',
      });

      const result = response.data as ExecutionResult;
      setReplHistory(prev => [
        ...prev,
        {
          input,
          output: result.stdout || result.stderr || '(No output)',
          error: result.exit_code !== 0,
        },
      ]);
    } catch (err: any) {
      setReplHistory(prev => [
        ...prev,
        {
          input,
          output: err.response?.data?.detail || err.message || 'Execution failed',
          error: true,
        },
      ]);
    } finally {
      setReplRunning(false);
      replInputRef.current?.focus();
    }
  };

  // REPL keyboard navigation
  const handleReplKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleReplExecute();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIndex);
        setReplInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setReplInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setReplInput('');
      }
    }
  };

  // Run tests
  const handleRunTests = async () => {
    if (!filePath) return;

    setTestRunning(true);
    setTestResults([]);
    setTestSummary(null);
    setTestRawOutput('');

    try {
      // Determine test file/directory - use current file if it's a test file, otherwise its directory
      const isTestFile = filePath.includes('test_') || filePath.includes('_test.py');
      const testTarget = isTestFile ? filePath : (filePath.includes('/') ? filePath.substring(0, filePath.lastIndexOf('/')) : '.');

      const response = await api.post(`/workspace/${projectId}/run-python`, {
        code: `
import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', '${testTarget}', '-v', '--tb=short'],
    capture_output=True,
    text=True,
    timeout=120
)

print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
`,
        file_path: '_test_runner_.py',
      });

      const result = response.data as ExecutionResult;
      const output = result.stdout + (result.stderr ? '\n' + result.stderr : '');
      setTestRawOutput(output);

      // Parse pytest verbose output (-v format: "test_file.py::test_name PASSED/FAILED")
      const results: TestResult[] = [];
      const lines = output.split('\n');
      let passed = 0, failed = 0, skipped = 0;

      for (const line of lines) {
        // Match verbose format: "test_file.py::TestClass::test_name PASSED" or "test_file.py::test_name PASSED"
        const verboseMatch = line.match(/^(.+::[\w_]+)\s+(PASSED|FAILED|SKIPPED|ERROR)/);
        if (verboseMatch) {
          const name = verboseMatch[1];
          const status = verboseMatch[2].toLowerCase() as TestResult['status'];
          results.push({ name, status, duration: 0 });
          if (status === 'passed') passed++;
          else if (status === 'failed') failed++;
          else if (status === 'skipped') skipped++;
        }
      }

      // Extract summary from pytest output (e.g., "1 passed in 0.03s" or "2 passed, 1 failed in 0.05s")
      const summaryMatch = output.match(/=+\s*([\d\w\s,]+)\s+in\s+([\d.]+)s\s*=+/);
      let duration = 0;
      if (summaryMatch) {
        duration = parseFloat(summaryMatch[2]);
        // Parse counts from summary if we didn't catch individual tests
        if (results.length === 0) {
          const passedMatch = summaryMatch[1].match(/(\d+)\s+passed/);
          const failedMatch = summaryMatch[1].match(/(\d+)\s+failed/);
          const skippedMatch = summaryMatch[1].match(/(\d+)\s+skipped/);
          passed = passedMatch ? parseInt(passedMatch[1]) : 0;
          failed = failedMatch ? parseInt(failedMatch[1]) : 0;
          skipped = skippedMatch ? parseInt(skippedMatch[1]) : 0;
        }
      }

      setTestResults(results);
      setTestSummary({ passed, failed, skipped, duration });
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Test execution failed';
      setTestRawOutput(errorMsg);
      setTestResults([{
        name: 'Test execution failed',
        status: 'error',
        duration: 0,
        message: errorMsg,
      }]);
    } finally {
      setTestRunning(false);
    }
  };

  // Profile code
  const handleProfile = async () => {
    if (!content) return;

    setProfileRunning(true);
    setProfileResults([]);

    try {
      const profileCode = `
import cProfile
import pstats
import io
from pstats import SortKey

# Original code to profile
code = '''${content.replace(/'/g, "\\'")}'''

profiler = cProfile.Profile()
profiler.enable()

try:
    exec(code)
except Exception as e:
    print(f"Error: {e}")

profiler.disable()

# Output stats
stream = io.StringIO()
stats = pstats.Stats(profiler, stream=stream).sort_stats(SortKey.CUMULATIVE)
stats.print_stats(20)

print("=== PROFILE RESULTS ===")
print(stream.getvalue())
`;

      const response = await api.post(`/workspace/${projectId}/run-python`, {
        code: profileCode,
        file_path: '_profiler_.py',
      });

      const output = (response.data as ExecutionResult).stdout;

      // Parse profile output
      const results: ProfileResult[] = [];
      const lines = output.split('\n');
      let inStats = false;
      let totalTime = 0;

      for (const line of lines) {
        if (line.includes('ncalls')) {
          inStats = true;
          continue;
        }
        if (inStats && line.trim()) {
          const parts = line.trim().split(/\s+/);
          if (parts.length >= 6 && !isNaN(parseInt(parts[0]))) {
            const calls = parseInt(parts[0].split('/')[0]);
            const tottime = parseFloat(parts[1]);
            const percall = parseFloat(parts[2]);
            const cumtime = parseFloat(parts[3]);
            const func = parts.slice(5).join(' ');

            if (func && !func.includes('<')) {
              results.push({
                function: func,
                calls,
                total_time: tottime,
                per_call: percall,
                cumulative: cumtime,
              });
              totalTime += tottime;
            }
          }
        }
      }

      setProfileResults(results.slice(0, 15)); // Top 15 functions
      setTotalProfileTime(totalTime);
    } catch (err: any) {
      console.error('Profile error:', err);
    } finally {
      setProfileRunning(false);
    }
  };

  const tabs = [
    { id: 'run' as TabType, label: 'Run', icon: Play, color: 'text-green-400' },
    { id: 'repl' as TabType, label: 'REPL', icon: TerminalIcon, color: 'text-cyan-400' },
    { id: 'tests' as TabType, label: 'Tests', icon: TestTube, color: 'text-purple-400' },
    { id: 'profile' as TabType, label: 'Profile', icon: BarChart3, color: 'text-amber-400' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e]">
      {/* Header with tabs */}
      <div className="border-b border-white/5 bg-[#252526]">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-green-400" />
            <span className="text-sm text-white font-medium">Python Dev Mode</span>
          </div>

          {filePath && (
            <span className="text-xs text-zinc-500 font-mono truncate max-w-[200px]">
              {filePath}
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-2">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-2 text-sm rounded-t-lg transition-all ${
                  isActive
                    ? 'bg-[#1e1e1e] text-white border-t border-l border-r border-white/10'
                    : 'text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? tab.color : ''}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {/* RUN TAB */}
        {activeTab === 'run' && (
          <div className="flex flex-col h-full">
            <div className="flex items-center justify-between p-3 border-b border-white/5">
              <button
                onClick={handleRun}
                disabled={running || !content}
                className="flex items-center gap-2 px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-300 text-sm rounded-lg border border-green-500/30 transition-all disabled:opacity-50"
              >
                {running ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Run File
                  </>
                )}
              </button>

              {runOutput && (
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <span>Exit: <span className={runOutput.exit_code === 0 ? 'text-green-400' : 'text-red-400'}>{runOutput.exit_code}</span></span>
                  <span>Time: <span className="text-cyan-400">{runOutput.execution_time.toFixed(3)}s</span></span>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
              {runError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
                  {runError}
                </div>
              )}

              {runOutput && (
                <div className="space-y-3">
                  {runOutput.stdout && (
                    <pre className="text-zinc-300 whitespace-pre-wrap">{runOutput.stdout}</pre>
                  )}
                  {runOutput.stderr && (
                    <pre className="text-red-400 whitespace-pre-wrap">{runOutput.stderr}</pre>
                  )}
                  {!runOutput.stdout && !runOutput.stderr && (
                    <p className="text-zinc-500 italic">No output</p>
                  )}
                </div>
              )}

              {!runOutput && !runError && (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <FileCode className="w-12 h-12 mb-3 opacity-50" />
                  <p>Click "Run File" to execute</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* REPL TAB */}
        {activeTab === 'repl' && (
          <div className="flex flex-col h-full">
            <div ref={replOutputRef} className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-3">
              {replHistory.length === 0 && (
                <div className="text-zinc-500 text-center py-8">
                  <TerminalIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Interactive Python REPL</p>
                  <p className="text-xs mt-1">Type code and press Enter</p>
                </div>
              )}

              {replHistory.map((entry, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-start gap-2">
                    <ChevronRight className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                    <pre className="text-cyan-300">{entry.input}</pre>
                  </div>
                  <div className="pl-6">
                    <pre className={`whitespace-pre-wrap ${entry.error ? 'text-red-400' : 'text-zinc-300'}`}>
                      {entry.output}
                    </pre>
                  </div>
                </div>
              ))}

              {replRunning && (
                <div className="flex items-center gap-2 text-zinc-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running...
                </div>
              )}
            </div>

            <div className="border-t border-white/5 p-3">
              <div className="flex items-center gap-2">
                <ChevronRight className="w-4 h-4 text-green-400" />
                <input
                  ref={replInputRef}
                  type="text"
                  value={replInput}
                  onChange={e => setReplInput(e.target.value)}
                  onKeyDown={handleReplKeyDown}
                  placeholder=">>> Enter Python code..."
                  className="flex-1 bg-transparent border-none outline-none text-sm font-mono text-cyan-300 placeholder:text-zinc-600"
                  disabled={replRunning}
                />
              </div>
            </div>
          </div>
        )}

        {/* TESTS TAB */}
        {activeTab === 'tests' && (
          <div className="flex flex-col h-full">
            <div className="flex items-center justify-between p-3 border-b border-white/5">
              <button
                onClick={handleRunTests}
                disabled={testRunning || !filePath}
                className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 text-sm rounded-lg border border-purple-500/30 transition-all disabled:opacity-50"
              >
                {testRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running Tests...
                  </>
                ) : (
                  <>
                    <TestTube className="w-4 h-4" />
                    Run pytest
                  </>
                )}
              </button>

              {testSummary && (
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-green-400">{testSummary.passed} passed</span>
                  <span className="text-red-400">{testSummary.failed} failed</span>
                  <span className="text-zinc-400">{testSummary.skipped} skipped</span>
                  <span className="text-cyan-400">{testSummary.duration.toFixed(2)}s</span>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {testResults.length === 0 && !testRunning && !testRawOutput && (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <TestTube className="w-12 h-12 mb-3 opacity-50" />
                  <p>Run pytest to see test results</p>
                  <p className="text-xs mt-1">Make sure your file is a test file (test_*.py or *_test.py)</p>
                </div>
              )}

              {/* Test results cards */}
              {testResults.length > 0 && (
                <div className="space-y-2 mb-4">
                  {testResults.map((test, idx) => (
                    <div
                      key={idx}
                      className={`flex items-center gap-3 p-3 rounded-lg border ${
                        test.status === 'passed'
                          ? 'bg-green-500/10 border-green-500/30'
                          : test.status === 'failed'
                          ? 'bg-red-500/10 border-red-500/30'
                          : test.status === 'skipped'
                          ? 'bg-zinc-500/10 border-zinc-500/30'
                          : 'bg-amber-500/10 border-amber-500/30'
                      }`}
                    >
                      <div className={`w-2 h-2 rounded-full ${
                        test.status === 'passed' ? 'bg-green-400' :
                        test.status === 'failed' ? 'bg-red-400' :
                        test.status === 'skipped' ? 'bg-zinc-400' : 'bg-amber-400'
                      }`} />
                      <span className="text-sm text-zinc-300 flex-1 font-mono truncate">{test.name}</span>
                      <span className={`text-xs uppercase ${
                        test.status === 'passed' ? 'text-green-400' :
                        test.status === 'failed' ? 'text-red-400' :
                        test.status === 'skipped' ? 'text-zinc-400' : 'text-amber-400'
                      }`}>
                        {test.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Raw pytest output */}
              {testRawOutput && (
                <div className="mt-4">
                  <div className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">Raw Output</div>
                  <pre className="text-xs text-zinc-400 bg-zinc-900/50 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono border border-white/5">
                    {testRawOutput}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* PROFILE TAB */}
        {activeTab === 'profile' && (
          <div className="flex flex-col h-full">
            <div className="flex items-center justify-between p-3 border-b border-white/5">
              <button
                onClick={handleProfile}
                disabled={profileRunning || !content}
                className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-sm rounded-lg border border-amber-500/30 transition-all disabled:opacity-50"
              >
                {profileRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Profiling...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Profile Code
                  </>
                )}
              </button>

              {totalProfileTime > 0 && (
                <span className="text-xs text-zinc-500">
                  Total: <span className="text-amber-400">{totalProfileTime.toFixed(4)}s</span>
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto">
              {profileResults.length === 0 && !profileRunning && (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <BarChart3 className="w-12 h-12 mb-3 opacity-50" />
                  <p>Profile your code to find bottlenecks</p>
                </div>
              )}

              {profileResults.length > 0 && (
                <table className="w-full text-sm">
                  <thead className="bg-zinc-800/50 sticky top-0">
                    <tr className="text-left text-xs text-zinc-500">
                      <th className="px-4 py-2">Function</th>
                      <th className="px-4 py-2 text-right">Calls</th>
                      <th className="px-4 py-2 text-right">Total (s)</th>
                      <th className="px-4 py-2 text-right">Cumulative</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profileResults.map((result, idx) => {
                      const percent = totalProfileTime > 0 ? (result.cumulative / totalProfileTime) * 100 : 0;
                      return (
                        <tr key={idx} className="border-t border-white/5 hover:bg-white/5">
                          <td className="px-4 py-2 font-mono text-cyan-300 truncate max-w-[200px]">
                            {result.function}
                          </td>
                          <td className="px-4 py-2 text-right text-zinc-400">{result.calls}</td>
                          <td className="px-4 py-2 text-right text-amber-400">{result.total_time.toFixed(4)}</td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2 justify-end">
                              <div className="w-20 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-amber-500 rounded-full"
                                  style={{ width: `${Math.min(percent, 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-zinc-400 w-12 text-right">
                                {result.cumulative.toFixed(4)}
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
