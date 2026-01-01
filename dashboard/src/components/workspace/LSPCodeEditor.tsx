/**
 * LSP-Enhanced Code Editor
 *
 * Wraps Monaco Editor with Language Server Protocol capabilities:
 * - Autocomplete
 * - Diagnostics (red squiggles)
 * - Hover tooltips
 * - Go-to-definition
 */

import React, { useEffect, useRef, useState, useImperativeHandle } from 'react';
import { CodeEditor, type CodeEditorHandle } from './CodeEditor';
import lspService from '../../services/lsp';
import * as monaco from 'monaco-editor';

// Global storage for provider disposables per language
const providerDisposables = new Map<string, monaco.IDisposable[]>();
const hoverDebounceTimers = new Map<string, number>();

interface LSPCodeEditorProps {
  projectId: number;
  filePath: string | null;
  onContentChange?: (content: string) => void;
  onSelectionChange?: (selectedText: string) => void;
}

/**
 * Register LSP providers for a language GLOBALLY before Monaco editor mounts.
 * This function should be called from the beforeMount callback.
 */
export function registerLSPProviders(
  monacoInstance: typeof monaco,
  language: string,
  projectId: number,
  getCurrentFilePath: () => string | null
) {
  // Skip if already registered for this language
  if (providerDisposables.has(language)) {
    console.log(`[LSP] Providers already registered for ${language}`);
    return;
  }

  console.log(`[LSP] Registering providers for ${language}`);

  const disposables: monaco.IDisposable[] = [];

  // Register Completion Provider
  disposables.push(
    monacoInstance.languages.registerCompletionItemProvider(language, {
      triggerCharacters: ['.', ':', '<', '(', '['],
      async provideCompletionItems(model, position) {
        const filePath = getCurrentFilePath();
        if (!filePath) return { suggestions: [] };

        const content = model.getValue();
        const line = position.lineNumber;
        const character = position.column - 1;

        try {
          const completions = await lspService.getCompletions(
            projectId,
            language,
            filePath,
            line,
            character,
            content
          );

          return {
            suggestions: completions.map(item => ({
              label: item.label,
              kind: item.kind as monaco.languages.CompletionItemKind,
              insertText: item.insertText,
              detail: item.detail,
              documentation: item.documentation,
              range: new monacoInstance.Range(
                position.lineNumber,
                position.column,
                position.lineNumber,
                position.column
              )
            }))
          } as monaco.languages.CompletionList;
        } catch (error) {
          console.error('[LSP] Completion error:', error);
          return { suggestions: [] };
        }
      }
    })
  );

  // Register Hover Provider
  disposables.push(
    monacoInstance.languages.registerHoverProvider(language, {
      provideHover(model, position) {
        console.log(`[HOVER] Triggered for ${language} at line ${position.lineNumber}, col ${position.column}`);

        const filePath = getCurrentFilePath();
        if (!filePath) {
          console.log('[HOVER] No file path available');
          return null;
        }

        return new Promise<monaco.languages.Hover | null>((resolve) => {
          // Debounce hover requests
          const timerKey = `${language}-hover`;
          const existingTimer = hoverDebounceTimers.get(timerKey);
          if (existingTimer) {
            clearTimeout(existingTimer);
          }

          const timer = window.setTimeout(async () => {
            const content = model.getValue();
            const line = position.lineNumber;
            const character = position.column - 1;

            console.log(`[HOVER] Requesting hover for ${filePath} at ${line}:${character}`);

            try {
              const hover = await lspService.getHover(
                projectId,
                language,
                filePath,
                line,
                character,
                content
              );

              console.log('[HOVER] Backend response:', hover);

              if (hover?.contents?.value) {
                const hoverContent = hover.contents.value;
                console.log(`[HOVER] ✓ Displaying documentation (${hoverContent.length} chars)`);

                resolve({
                  contents: [
                    {
                      value: hoverContent,
                      isTrusted: true,
                      supportHtml: false
                    }
                  ]
                } as monaco.languages.Hover);
              } else {
                console.log('[HOVER] No content in response');
                resolve(null);
              }
            } catch (error) {
              console.error('[HOVER] ❌ Error:', error);
              resolve(null);
            }

            hoverDebounceTimers.delete(timerKey);
          }, 200);

          hoverDebounceTimers.set(timerKey, timer);
        });
      }
    })
  );

  // Register Definition Provider
  disposables.push(
    monacoInstance.languages.registerDefinitionProvider(language, {
      async provideDefinition(model, position) {
        const filePath = getCurrentFilePath();
        if (!filePath) return null;

        const content = model.getValue();
        const line = position.lineNumber;
        const character = position.column - 1;

        try {
          const definition = await lspService.getDefinition(
            projectId,
            language,
            filePath,
            line,
            character,
            content
          );

          if (definition?.uri) {
            const defFilePath = definition.uri.replace('file://', '');

            return {
              uri: monacoInstance.Uri.file(defFilePath),
              range: {
                startLineNumber: definition.range.start.line + 1,
                startColumn: definition.range.start.character + 1,
                endLineNumber: definition.range.end.line + 1,
                endColumn: definition.range.end.character + 1
              }
            };
          }
        } catch (error) {
          console.error('[LSP] Definition error:', error);
        }

        return null;
      }
    })
  );

  providerDisposables.set(language, disposables);
  console.log(`✓ LSP providers registered for ${language}`);
}

export const LSPCodeEditor = React.forwardRef<CodeEditorHandle, LSPCodeEditorProps>(
  ({ projectId, filePath, onContentChange, onSelectionChange }, ref) => {
  const editorRef = useRef<CodeEditorHandle>(null);
  const [lspEnabled, setLspEnabled] = useState(false);
  const [language, setLanguage] = useState<string | null>(null);
  const debounceTimer = useRef<number | null>(null);
  const selectionDebounceTimer = useRef<number | null>(null);
  const currentFilePathRef = useRef<string | null>(null);

  // Keep track of current file path for provider callbacks
  currentFilePathRef.current = filePath;

  // Expose the editor instance to parent components
  useImperativeHandle(ref, () => ({
    getEditor: () => editorRef.current?.getEditor() || null,
    getMonaco: () => editorRef.current?.getMonaco() || null
  }));

  // Listen for selection changes
  useEffect(() => {
    if (!onSelectionChange) return;

    const editor = editorRef.current?.getEditor();
    if (!editor) {
      // Editor not ready yet, retry after mount
      const retryTimer = setTimeout(() => {
        const ed = editorRef.current?.getEditor();
        if (ed && onSelectionChange) {
          const disposable = ed.onDidChangeCursorSelection(() => {
            // Debounce selection change notifications
            if (selectionDebounceTimer.current) {
              clearTimeout(selectionDebounceTimer.current);
            }
            selectionDebounceTimer.current = window.setTimeout(() => {
              const selection = ed.getSelection();
              if (selection && !selection.isEmpty()) {
                const selectedText = ed.getModel()?.getValueInRange(selection) || '';
                onSelectionChange(selectedText);
              } else {
                onSelectionChange('');
              }
            }, 150);
          });
          return () => disposable.dispose();
        }
      }, 500);
      return () => clearTimeout(retryTimer);
    }

    const disposable = editor.onDidChangeCursorSelection(() => {
      // Debounce selection change notifications
      if (selectionDebounceTimer.current) {
        clearTimeout(selectionDebounceTimer.current);
      }
      selectionDebounceTimer.current = window.setTimeout(() => {
        const selection = editor.getSelection();
        if (selection && !selection.isEmpty()) {
          const selectedText = editor.getModel()?.getValueInRange(selection) || '';
          onSelectionChange(selectedText);
        } else {
          onSelectionChange('');
        }
      }, 150);
    });

    return () => {
      disposable.dispose();
      if (selectionDebounceTimer.current) {
        clearTimeout(selectionDebounceTimer.current);
      }
    };
  }, [onSelectionChange, filePath]);

  useEffect(() => {
    if (!filePath) {
      setLspEnabled(false);
      setLanguage(null);
      return;
    }

    // Detect language from file path
    const detectedLanguage = lspService.getLanguageFromPath(filePath);
    setLanguage(detectedLanguage);

    if (!detectedLanguage) {
      setLspEnabled(false);
      return;
    }

    let mounted = true;
    let retryCount = 0;
    const MAX_RETRIES = 50; // Max 5 seconds of waiting (50 * 100ms)
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    // Initialize LSP server AND register providers globally
    const initLSP = async () => {
      try {
        await lspService.initialize(
          projectId,
          detectedLanguage,
          `/workspace/${projectId}`
        );

        // Wait for Monaco to be available from CodeEditor ref
        const tryRegisterProviders = () => {
          if (!mounted) return; // Component unmounted, stop retrying

          const monacoInstance = editorRef.current?.getMonaco?.();
          if (monacoInstance) {
            console.log('[LSP] Monaco instance retrieved from editor ref');
            // Register providers globally for this language
            registerLSPProviders(
              monacoInstance,
              detectedLanguage,
              projectId,
              () => currentFilePathRef.current
            );
            setLspEnabled(true);
            console.log(`✓ LSP enabled for ${detectedLanguage}`);
          } else if (retryCount < MAX_RETRIES) {
            // Monaco not yet available, retry in 100ms
            retryCount++;
            if (retryCount % 10 === 0) {
              console.log(`[LSP] Waiting for Monaco instance... (${retryCount}/${MAX_RETRIES})`);
            }
            timeoutId = setTimeout(tryRegisterProviders, 100);
          } else {
            console.warn('[LSP] Max retries reached, Monaco instance not available');
            setLspEnabled(false);
          }
        };

        tryRegisterProviders();
      } catch (error) {
        console.error('LSP initialization failed:', error);
        setLspEnabled(false);
      }
    };

    initLSP();

    return () => {
      mounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [projectId, filePath]);

  useEffect(() => {
    if (!lspEnabled || !language || !filePath) return;

    const editor = editorRef.current?.getEditor();
    if (!editor) return;

    // Update diagnostics on content change (debounced)
    const updateDiagnostics = async () => {
      const content = editor.getValue();

      try {
        const diagnostics = await lspService.getDiagnostics(
          projectId,
          language,
          filePath,
          content
        );

        const model = editor.getModel();
        if (!model) return;

        const markers = diagnostics.map(diag => ({
          severity: diag.severity as monaco.MarkerSeverity,
          startLineNumber: diag.range.start.line + 1,
          startColumn: diag.range.start.character + 1,
          endLineNumber: diag.range.end.line + 1,
          endColumn: diag.range.end.character + 1,
          message: diag.message,
          source: diag.source
        }));

        monaco.editor.setModelMarkers(model, language, markers);
      } catch (error) {
        console.error('Diagnostics error:', error);
      }
    };

    // Trigger diagnostics on content change (debounced)
    const handleContentChange = () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }

      debounceTimer.current = window.setTimeout(updateDiagnostics, 500);
    };

    const changeDisposable = editor.onDidChangeModelContent(handleContentChange);

    // Initial diagnostics
    updateDiagnostics();

    // Cleanup
    return () => {
      changeDisposable.dispose();

      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [lspEnabled, language, filePath, projectId]);

  return (
    <div className="relative h-full">
      {/* LSP Status Indicator */}
      {lspEnabled && (
        <div className="absolute top-2 right-2 z-10">
          <div className="px-2 py-1 rounded bg-green-500/20 border border-green-500/30 text-green-400 text-xs flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            LSP: {language}
          </div>
        </div>
      )}

      <CodeEditor
        ref={editorRef}
        projectId={projectId}
        filePath={filePath}
        onContentChange={onContentChange}
      />
    </div>
  );
});
