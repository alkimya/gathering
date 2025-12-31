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

interface LSPCodeEditorProps {
  projectId: number;
  filePath: string | null;
  onContentChange?: (content: string) => void;
}

export const LSPCodeEditor = React.forwardRef<CodeEditorHandle, LSPCodeEditorProps>(
  ({ projectId, filePath, onContentChange }, ref) => {
  const editorRef = useRef<CodeEditorHandle>(null);
  const [lspEnabled, setLspEnabled] = useState(false);
  const [language, setLanguage] = useState<string | null>(null);
  const debounceTimer = useRef<number | null>(null);
  const hoverDebounceTimer = useRef<number | null>(null);

  // Expose the editor instance to parent components
  useImperativeHandle(ref, () => ({
    getEditor: () => editorRef.current?.getEditor() || null
  }));

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

    // Initialize LSP server
    const initLSP = async () => {
      try {
        await lspService.initialize(
          projectId,
          detectedLanguage,
          `/workspace/${projectId}`
        );
        setLspEnabled(true);
        console.log(`✓ LSP enabled for ${detectedLanguage}`);
      } catch (error) {
        console.error('LSP initialization failed:', error);
        setLspEnabled(false);
      }
    };

    initLSP();
  }, [projectId, filePath]);

  useEffect(() => {
    if (!lspEnabled || !language || !filePath) return;

    const editor = editorRef.current?.getEditor();
    if (!editor) return;

    console.log('✓ Setting up LSP providers for', language, 'file:', filePath);

    // Register Completion Provider
    const completionDisposable = monaco.languages.registerCompletionItemProvider(
      language,
      {
        triggerCharacters: ['.', ':', '<', '(', '['],
        async provideCompletionItems(model, position) {
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
                range: new monaco.Range(
                  position.lineNumber,
                  position.column,
                  position.lineNumber,
                  position.column
                )
              }))
            } as monaco.languages.CompletionList;
          } catch (error) {
            console.error('Completion error:', error);
            return { suggestions: [] };
          }
        }
      }
    );

    // Register Hover Provider with debounce
    const hoverDisposable = monaco.languages.registerHoverProvider(
      language,
      {
        provideHover(model, position) {
          console.log(`[HOVER] Triggered at line ${position.lineNumber}, col ${position.column}`);

          // Return a promise that debounces the hover request
          return new Promise<monaco.languages.Hover | null>((resolve) => {
            if (hoverDebounceTimer.current) {
              clearTimeout(hoverDebounceTimer.current);
            }

            hoverDebounceTimer.current = window.setTimeout(async () => {
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
                  console.log('[HOVER] ✓ Displaying documentation (' + hoverContent.length + ' chars)');

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
            }, 200); // 200ms debounce for hover
          });
        }
      }
    );

    console.log('✓ Hover provider registered for', language);

    // Register Definition Provider
    const definitionDisposable = monaco.languages.registerDefinitionProvider(
      language,
      {
        async provideDefinition(model, position) {
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
              // Parse file:// URI
              const filePath = definition.uri.replace('file://', '');

              return {
                uri: monaco.Uri.file(filePath),
                range: {
                  startLineNumber: definition.range.start.line + 1,
                  startColumn: definition.range.start.character + 1,
                  endLineNumber: definition.range.end.line + 1,
                  endColumn: definition.range.end.character + 1
                }
              };
            }
          } catch (error) {
            console.error('Definition error:', error);
          }

          return null;
        }
      }
    );

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
      completionDisposable.dispose();
      hoverDisposable.dispose();
      definitionDisposable.dispose();
      changeDisposable.dispose();

      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
      if (hoverDebounceTimer.current) {
        clearTimeout(hoverDebounceTimer.current);
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
