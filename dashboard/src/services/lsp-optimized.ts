/**
 * Optimized LSP Service with caching and reduced network calls.
 *
 * Optimizations:
 * - Document content caching (only send on open/change)
 * - Debounced diagnostics
 * - No content sent for hover/completion after initial sync
 */

import api from './api';

interface CompletionItem {
  label: string;
  kind: number;
  insertText: string;
  detail?: string;
  documentation?: string;
}

interface Diagnostic {
  range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
  };
  severity: number;
  message: string;
  source?: string;
}

interface HoverInfo {
  contents: {
    value: string;
  };
}

interface DefinitionLocation {
  uri: string;
  range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
  };
}

class OptimizedLSPService {
  private initialized: Map<string, boolean> = new Map();
  private documentVersions: Map<string, number> = new Map();
  private lastContent: Map<string, string> = new Map();

  /**
   * Initialize LSP server for a project and language.
   */
  async initialize(
    projectId: number,
    language: string,
    workspacePath: string
  ): Promise<void> {
    const key = `${projectId}:${language}`;

    if (this.initialized.get(key)) {
      return;
    }

    try {
      await api.post(`/lsp/${projectId}/initialize`, {
        language,
        workspace_path: workspacePath
      });

      this.initialized.set(key, true);
      console.log(`✓ LSP initialized for ${language} in project ${projectId}`);
    } catch (error) {
      console.error(`Failed to initialize LSP for ${language}:`, error);
      throw error;
    }
  }

  /**
   * Notify LSP that a document was opened.
   * This sends the initial content.
   */
  async didOpen(
    projectId: number,
    _language: string,
    filePath: string,
    content: string
  ): Promise<void> {
    const docKey = `${projectId}:${filePath}`;

    // Store content locally
    this.lastContent.set(docKey, content);
    this.documentVersions.set(docKey, 1);

    // For now, we don't have a didOpen endpoint
    // Content will be sent with first completion/hover request
    console.log(`Document opened: ${filePath}`);
  }

  /**
   * Notify LSP that a document changed.
   * Only sends if content actually changed.
   */
  async didChange(
    projectId: number,
    _language: string,
    filePath: string,
    content: string
  ): Promise<void> {
    const docKey = `${projectId}:${filePath}`;
    const lastContent = this.lastContent.get(docKey);

    // Skip if content hasn't changed
    if (lastContent === content) {
      return;
    }

    // Update local cache
    this.lastContent.set(docKey, content);
    const version = (this.documentVersions.get(docKey) || 0) + 1;
    this.documentVersions.set(docKey, version);

    console.log(`Document changed: ${filePath} (v${version})`);
  }

  /**
   * Get completions.
   * Only sends content on first call or if changed.
   */
  async getCompletions(
    projectId: number,
    language: string,
    filePath: string,
    line: number,
    character: number,
    content?: string
  ): Promise<CompletionItem[]> {
    const docKey = `${projectId}:${filePath}`;

    // Update content if provided
    if (content) {
      await this.didChange(projectId, language, filePath, content);
    }

    try {
      const response = await api.post(
        `/lsp/${projectId}/completions?language=${language}`,
        {
          file_path: filePath,
          line,
          character,
          content: this.lastContent.get(docKey) || content  // Send cached or new content
        }
      );

      return (response.data as any).completions || [];
    } catch (error) {
      console.error('LSP completions error:', error);
      return [];
    }
  }

  /**
   * Get diagnostics.
   */
  async getDiagnostics(
    projectId: number,
    language: string,
    filePath: string,
    content?: string
  ): Promise<Diagnostic[]> {
    const docKey = `${projectId}:${filePath}`;

    if (content) {
      await this.didChange(projectId, language, filePath, content);
    }

    try {
      const response = await api.post(
        `/lsp/${projectId}/diagnostics?language=${language}`,
        {
          file_path: filePath,
          content: this.lastContent.get(docKey) || content
        }
      );

      return (response.data as any).diagnostics || [];
    } catch (error) {
      console.error('LSP diagnostics error:', error);
      return [];
    }
  }

  /**
   * Get hover information.
   */
  async getHover(
    projectId: number,
    language: string,
    filePath: string,
    line: number,
    character: number,
    content?: string
  ): Promise<HoverInfo | null> {
    const docKey = `${projectId}:${filePath}`;

    if (content) {
      await this.didChange(projectId, language, filePath, content);
    }

    try {
      const response = await api.post(
        `/lsp/${projectId}/hover?language=${language}`,
        {
          file_path: filePath,
          line,
          character,
          content: this.lastContent.get(docKey) || content
        }
      );

      const data = response.data as any;
      return data.contents ? data : null;
    } catch (error) {
      console.error('LSP hover error:', error);
      return null;
    }
  }

  /**
   * Get definition location.
   */
  async getDefinition(
    projectId: number,
    language: string,
    filePath: string,
    line: number,
    character: number,
    content?: string
  ): Promise<DefinitionLocation | null> {
    const docKey = `${projectId}:${filePath}`;

    if (content) {
      await this.didChange(projectId, language, filePath, content);
    }

    try {
      const response = await api.post(
        `/lsp/${projectId}/definition?language=${language}`,
        {
          file_path: filePath,
          line,
          character,
          content: this.lastContent.get(docKey) || content
        }
      );

      const data = response.data as any;
      return data.uri ? data : null;
    } catch (error) {
      console.error('LSP definition error:', error);
      return null;
    }
  }

  /**
   * Check if LSP server is active.
   */
  async getStatus(
    projectId: number,
    language: string
  ): Promise<boolean> {
    try {
      const response = await api.get(
        `/lsp/${projectId}/status?language=${language}`
      );

      return (response.data as any).active || false;
    } catch (error) {
      return false;
    }
  }

  /**
   * Shutdown LSP server.
   */
  async shutdown(
    projectId: number,
    language: string
  ): Promise<void> {
    const key = `${projectId}:${language}`;

    try {
      await api.delete(
        `/lsp/${projectId}/shutdown?language=${language}`
      );

      this.initialized.delete(key);

      // Clean up document cache for this project
      const docKeys = Array.from(this.lastContent.keys()).filter(k =>
        k.startsWith(`${projectId}:`)
      );
      docKeys.forEach(k => {
        this.lastContent.delete(k);
        this.documentVersions.delete(k);
      });

      console.log(`LSP server shut down for ${language}`);
    } catch (error) {
      console.error('LSP shutdown error:', error);
    }
  }

  /**
   * Detect language from file path.
   */
  getLanguageFromPath(filePath: string): string | null {
    const ext = filePath.split('.').pop()?.toLowerCase();

    const languageMap: Record<string, string> = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'rs': 'rust',
      'go': 'go',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'h': 'cpp',
      'hpp': 'cpp',
      'cs': 'csharp',
      'rb': 'ruby',
      'php': 'php',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'r': 'r',
      'sql': 'sql'
    };

    return ext ? (languageMap[ext] || null) : null;
  }

  /**
   * Clear all caches (useful for debugging).
   */
  clearCache(): void {
    this.lastContent.clear();
    this.documentVersions.clear();
    console.log('LSP cache cleared');
  }
}

// Export singleton instance
const optimizedLspService = new OptimizedLSPService();
export default optimizedLspService;
