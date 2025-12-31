/**
 * Workspace Page - IDE-like development environment
 * Web3 Dark Theme - Phase 7.2 with Terminal & Markdown Preview
 * OPTIMIZED: Lazy loading for heavy components
 */

import { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FolderTree, Activity, Terminal as TerminalIcon, Maximize2, Minimize2, GitBranch, Eye, SplitSquareHorizontal, Loader2 } from 'lucide-react';
import { FileExplorerOptimized as FileExplorer } from '../components/workspace/FileExplorerOptimized';
import { type CodeEditorHandle } from '../components/workspace/CodeEditor';
import { GitTimeline } from '../components/workspace/GitTimeline';
import { ActivityFeed } from '../components/workspace/ActivityFeed';
import { ResizablePanels } from '../components/workspace/ResizablePanels';
import api from '../services/api';

// Lazy load heavy Monaco Editor components (only when file is selected)
const LSPCodeEditor = lazy(() => import('../components/workspace/LSPCodeEditor').then(m => ({ default: m.LSPCodeEditor })));

// Lazy load preview components (only when needed)
const Terminal = lazy(() => import('../components/workspace/Terminal').then(m => ({ default: m.Terminal })));
const MarkdownPreview = lazy(() => import('../components/workspace/MarkdownPreview').then(m => ({ default: m.MarkdownPreview })));
const HTMLPreview = lazy(() => import('../components/workspace/HTMLPreview').then(m => ({ default: m.HTMLPreview })));
const PythonRunner = lazy(() => import('../components/workspace/PythonRunner').then(m => ({ default: m.PythonRunner })));
const ImagePreview = lazy(() => import('../components/workspace/ImagePreview').then(m => ({ default: m.ImagePreview })));
const JSONPreview = lazy(() => import('../components/workspace/JSONPreview').then(m => ({ default: m.JSONPreview })));
const CSVPreview = lazy(() => import('../components/workspace/CSVPreview').then(m => ({ default: m.CSVPreview })));
const VideoPreview = lazy(() => import('../components/workspace/VideoPreview').then(m => ({ default: m.VideoPreview })));
const AudioPreview = lazy(() => import('../components/workspace/AudioPreview').then(m => ({ default: m.AudioPreview })));

// Import types separately
import type { MarkdownPreviewHandle } from '../components/workspace/MarkdownPreview';

// Loading component for lazy-loaded components
function ComponentLoader() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <Loader2 className="w-6 h-6 text-purple-500 animate-spin mx-auto mb-2" />
        <p className="text-zinc-500 text-xs">Chargement...</p>
      </div>
    </div>
  );
}

interface WorkspaceInfo {
  type: string;
  path: string;
  name: string;
  file_count: number;
  size_mb: number;
  is_git_repo: boolean;
  capabilities: string[];
}

export function Workspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const [workspaceInfo, setWorkspaceInfo] = useState<WorkspaceInfo | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Layout state
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [showActivityFeed, setShowActivityFeed] = useState(true);
  const [showTerminal, setShowTerminal] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Refs for scroll sync
  const codeEditorRef = useRef<CodeEditorHandle>(null);
  const markdownPreviewRef = useRef<MarkdownPreviewHandle>(null);

  // Scroll sync state
  const isSyncingRef = useRef(false);

  useEffect(() => {
    loadWorkspaceInfo();
  }, [projectId]);

  // Setup bidirectional scroll sync for markdown files
  useEffect(() => {
    const isMarkdown = selectedFile?.endsWith('.md');
    if (!isMarkdown || !showPreview) return;

    // Delay to ensure editor and preview are fully mounted
    const setupSync = () => {
      const editor = codeEditorRef.current?.getEditor();
      const previewContainer = markdownPreviewRef.current?.getScrollContainer();

      if (!editor || !previewContainer) {
        console.log('Scroll sync waiting - editor:', !!editor, 'preview:', !!previewContainer);
        return null;
      }

      console.log('✓ Scroll sync activated for markdown', {
        editorLines: editor.getModel()?.getLineCount(),
        previewHeight: previewContainer.scrollHeight
      });

      // Editor scroll -> Preview scroll
      const editorScrollDisposable = editor.onDidScrollChange(() => {
        if (isSyncingRef.current) return;
        isSyncingRef.current = true;

        try {
          const visibleRange = editor.getVisibleRanges()[0];
          if (visibleRange) {
            const totalLines = editor.getModel()?.getLineCount() || 1;
            const scrollPercentage = visibleRange.startLineNumber / totalLines;

            const maxScroll = previewContainer.scrollHeight - previewContainer.clientHeight;
            const newScrollTop = scrollPercentage * maxScroll;

            console.log('Editor → Preview:', {
              line: visibleRange.startLineNumber,
              totalLines,
              scrollPercentage: (scrollPercentage * 100).toFixed(1) + '%',
              newScrollTop
            });

            previewContainer.scrollTop = newScrollTop;
          }
        } finally {
          setTimeout(() => { isSyncingRef.current = false; }, 150);
        }
      });

      // Preview scroll -> Editor scroll
      const handlePreviewScroll = () => {
        if (isSyncingRef.current) return;
        isSyncingRef.current = true;

        try {
          const scrollPercentage = previewContainer.scrollTop /
            (previewContainer.scrollHeight - previewContainer.clientHeight);

          const totalLines = editor.getModel()?.getLineCount() || 1;
          const targetLine = Math.round(scrollPercentage * totalLines);

          console.log('Preview → Editor:', {
            scrollTop: previewContainer.scrollTop,
            scrollHeight: previewContainer.scrollHeight,
            scrollPercentage: (scrollPercentage * 100).toFixed(1) + '%',
            targetLine,
            totalLines
          });

          editor.revealLineInCenter(targetLine);
        } finally {
          setTimeout(() => { isSyncingRef.current = false; }, 150);
        }
      };

      previewContainer.addEventListener('scroll', handlePreviewScroll);

      return () => {
        editorScrollDisposable?.dispose();
        previewContainer.removeEventListener('scroll', handlePreviewScroll);
      };
    };

    // Try immediately
    let cleanup = setupSync();
    let syncActivated = !!cleanup;

    // If failed, retry after delays
    const retryIntervals = [100, 300, 500, 1000];
    const timeouts: number[] = [];

    if (!syncActivated) {
      console.log('Scroll sync not ready, will retry...');
      retryIntervals.forEach(delay => {
        const timeoutId = window.setTimeout(() => {
          if (!syncActivated) {
            const result = setupSync();
            if (result) {
              cleanup = result;
              syncActivated = true;
            }
          }
        }, delay);
        timeouts.push(timeoutId);
      });
    }

    return () => {
      if (cleanup) {
        cleanup();
      }
      timeouts.forEach(id => window.clearTimeout(id));
    };
  }, [selectedFile, showPreview]);

  useEffect(() => {
    // Auto-show preview for supported file types
    if (!selectedFile) {
      setShowPreview(false);
      return;
    }

    const ext = selectedFile.toLowerCase();

    // Check for previewable file types
    const hasPreview =
      ext.endsWith('.md') ||
      ext.endsWith('.html') || ext.endsWith('.htm') ||
      ext.endsWith('.py') ||
      ext.endsWith('.json') ||
      ext.endsWith('.csv') || ext.endsWith('.tsv') ||
      ext.endsWith('.png') || ext.endsWith('.jpg') || ext.endsWith('.jpeg') ||
      ext.endsWith('.gif') || ext.endsWith('.svg') || ext.endsWith('.webp') ||
      ext.endsWith('.mp4') || ext.endsWith('.webm') || ext.endsWith('.avi') || ext.endsWith('.mov') ||
      ext.endsWith('.mp3') || ext.endsWith('.wav') || ext.endsWith('.ogg') || ext.endsWith('.m4a');

    setShowPreview(hasPreview);
  }, [selectedFile]);

  const loadWorkspaceInfo = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      const response = await api.get(`/workspace/${projectId}/info`);
      setWorkspaceInfo(response.data as WorkspaceInfo);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load workspace info:', err);
      setError(err.response?.data?.detail || 'Failed to load workspace');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (filePath: string) => {
    setSelectedFile(filePath);
  };

  const handleFileContentChange = (content: string) => {
    setFileContent(content);
  };

  // File type detection
  const ext = selectedFile?.toLowerCase() || '';
  const isMarkdownFile = ext.endsWith('.md');
  const isHTMLFile = ext.endsWith('.html') || ext.endsWith('.htm');
  const isPythonFile = ext.endsWith('.py');
  const isJSONFile = ext.endsWith('.json');
  const isCSVFile = ext.endsWith('.csv') || ext.endsWith('.tsv');
  const isImageFile = ext.endsWith('.png') || ext.endsWith('.jpg') || ext.endsWith('.jpeg') ||
                       ext.endsWith('.gif') || ext.endsWith('.svg') || ext.endsWith('.webp');
  const isVideoFile = ext.endsWith('.mp4') || ext.endsWith('.webm') || ext.endsWith('.avi') || ext.endsWith('.mov');
  const isAudioFile = ext.endsWith('.mp3') || ext.endsWith('.wav') || ext.endsWith('.ogg') || ext.endsWith('.m4a');

  const hasPreview = isMarkdownFile || isHTMLFile || isPythonFile || isJSONFile || isCSVFile || isImageFile || isVideoFile || isAudioFile;

  const getPreviewIcon = () => {
    if (isPythonFile) return TerminalIcon;
    return Eye;
  };

  const PreviewIcon = getPreviewIcon();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-mesh">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-500 mx-auto mb-6 glow-purple"></div>
            <div className="absolute inset-0 rounded-full h-16 w-16 border-t-2 border-cyan-500 mx-auto animate-spin" style={{ animationDuration: '1.5s', animationDirection: 'reverse' }}></div>
          </div>
          <p className="text-zinc-300 text-lg">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-mesh">
        <div className="text-center glass-card p-8 rounded-xl max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-white mb-3">Workspace Error</h2>
          <p className="text-zinc-400 mb-6">{error}</p>
          <button onClick={loadWorkspaceInfo} className="btn-gradient px-6 py-3 rounded-lg">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-mesh">
      {/* Header */}
      <div className="glass-card border-b border-white/5 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projectId}`} className="p-2 hover:bg-white/5 rounded-lg transition-colors group">
            <ArrowLeft className="w-5 h-5 text-zinc-400 group-hover:text-purple-400 transition-colors" />
          </Link>

          <div className="h-8 w-px bg-white/10"></div>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center glow-purple">
              <FolderTree className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">{workspaceInfo?.name}</h1>
              <p className="text-xs text-zinc-500">
                {workspaceInfo?.file_count?.toLocaleString()} files • {workspaceInfo?.size_mb?.toFixed(1)} MB
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-purple-500/10 text-purple-400 text-xs font-medium rounded-lg border border-purple-500/20">
              {workspaceInfo?.type}
            </span>
            {workspaceInfo?.is_git_repo && (
              <span className="px-3 py-1 bg-cyan-500/10 text-cyan-400 text-xs font-medium rounded-lg border border-cyan-500/20 flex items-center gap-1">
                <GitBranch className="w-3 h-3" />
                Git
              </span>
            )}
          </div>
        </div>

        {/* View toggles */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFileExplorer(!showFileExplorer)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
              showFileExplorer
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
            }`}
          >
            <FolderTree className="w-4 h-4" />
            Files
          </button>
          <button
            onClick={() => setShowActivityFeed(!showActivityFeed)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
              showActivityFeed
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
            }`}
          >
            <Activity className="w-4 h-4" />
            Activity
          </button>
          <button
            onClick={() => setShowTerminal(!showTerminal)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
              showTerminal
                ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
            }`}
          >
            <TerminalIcon className="w-4 h-4" />
            Terminal
          </button>

          {hasPreview && (
            <button
              onClick={() => setShowPreview(!showPreview)}
              className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
                showPreview
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
              }`}
            >
              {showPreview && !isPythonFile ? <SplitSquareHorizontal className="w-4 h-4" /> : <PreviewIcon className="w-4 h-4" />}
              {isPythonFile ? 'Run' : 'Preview'}
            </button>
          )}

          <div className="h-8 w-px bg-white/10"></div>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4 text-zinc-400 group-hover:text-purple-400 transition-colors" />
            ) : (
              <Maximize2 className="w-4 h-4 text-zinc-400 group-hover:text-purple-400 transition-colors" />
            )}
          </button>
        </div>
      </div>

      {/* Main workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer - Full height */}
        {showFileExplorer && (
          <div className="w-80 glass-card border-r border-white/5 flex flex-col">
            <FileExplorer
              projectId={parseInt(projectId || '0')}
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
            />
          </div>
        )}

        {/* Center: Editor + Terminal */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Editor/Preview area */}
          <div className="flex-1 overflow-hidden">
            {hasPreview && showPreview ? (
              <ResizablePanels
                left={
                  // Images don't need editor, show full preview
                  isImageFile ? (
                    <div className="h-full" />
                  ) : (
                    <Suspense fallback={<ComponentLoader />}>
                      <LSPCodeEditor
                        ref={codeEditorRef}
                        projectId={parseInt(projectId || '0')}
                        filePath={selectedFile}
                        onContentChange={handleFileContentChange}
                      />
                    </Suspense>
                  )
                }
                right={
                  <Suspense fallback={<ComponentLoader />}>
                    {isMarkdownFile && <MarkdownPreview ref={markdownPreviewRef} content={fileContent} />}
                    {isHTMLFile && <HTMLPreview content={fileContent} />}
                    {isPythonFile && (
                      <PythonRunner
                        projectId={parseInt(projectId || '0')}
                        filePath={selectedFile}
                        content={fileContent}
                      />
                    )}
                    {isJSONFile && <JSONPreview content={fileContent} />}
                    {isCSVFile && <CSVPreview content={fileContent} filePath={selectedFile || undefined} />}
                    {isImageFile && selectedFile && (
                      <ImagePreview
                        projectId={parseInt(projectId || '0')}
                        filePath={selectedFile}
                      />
                    )}
                    {isVideoFile && selectedFile && (
                      <VideoPreview
                        projectId={parseInt(projectId || '0')}
                        filePath={selectedFile}
                      />
                    )}
                    {isAudioFile && selectedFile && (
                      <AudioPreview
                        projectId={parseInt(projectId || '0')}
                        filePath={selectedFile}
                      />
                    )}
                  </Suspense>
                }
                defaultLeftWidth={isPythonFile ? 65 : (isImageFile || isVideoFile || isAudioFile) ? 0 : 50}
                minLeftWidth={(isImageFile || isVideoFile || isAudioFile) ? 0 : 30}
                minRightWidth={isPythonFile ? 25 : (isImageFile || isVideoFile || isAudioFile) ? 100 : 30}
              />
            ) : (
              <Suspense fallback={<ComponentLoader />}>
                <LSPCodeEditor
                  projectId={parseInt(projectId || '0')}
                  filePath={selectedFile}
                  onContentChange={handleFileContentChange}
                />
              </Suspense>
            )}
          </div>

          {/* Terminal - Only under editor */}
          {showTerminal && (
            <div className="h-64 border-t border-white/5">
              <Suspense fallback={<ComponentLoader />}>
                <Terminal projectId={parseInt(projectId || '0')} />
              </Suspense>
            </div>
          )}
        </div>

        {/* Right Panel: Activity Feed + Git Timeline - Full height */}
        {showActivityFeed && (
          <div className="w-96 glass-card border-l border-white/5 flex flex-col">
            <div className="flex-1 overflow-hidden flex flex-col border-b border-white/5">
              <ActivityFeed projectId={parseInt(projectId || '0')} />
            </div>
            {workspaceInfo?.is_git_repo && (
              <div className="flex-1 overflow-hidden flex flex-col">
                <GitTimeline projectId={parseInt(projectId || '0')} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
