/**
 * LSP Service - Language Server Protocol client.
 *
 * Provides autocomplete, diagnostics, hover, and go-to-definition
 * for Monaco Editor using our backend LSP servers.
 */

import api from './api';

export interface CompletionItem {
  label: string;
  kind: number;
  detail?: string;
  insertText: string;
  documentation?: string;
}

export interface Diagnostic {
  range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
  };
  severity: number; // 1=Error, 2=Warning, 3=Info, 4=Hint
  message: string;
  source: string;
}

export interface HoverInfo {
  contents: {
    kind: 'markdown' | 'plaintext';
    value: string;
  };
}

export interface DefinitionLocation {
  uri: string;
  range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
  };
}

class LSPService {
  private initialized: Map<string, boolean> = new Map();

  /**
   * Initialize LSP server for a language.
   */
  async initialize(
    projectId: number,
    language: string,
    workspacePath: string
  ): Promise<void> {
    const key = `${projectId}:${language}`;

    if (this.initialized.get(key)) {
      return; // Already initialized
    }

    try {
      await api.post(`/lsp/${projectId}/initialize`, {
        language,
        workspace_path: workspacePath
      });

      this.initialized.set(key, true);
      console.log(`✓ LSP initialized for ${language}`);
    } catch (error) {
      console.error(`LSP initialization failed for ${language}:`, error);
      throw error;
    }
  }

  /**
   * Get autocomplete suggestions.
   */
  async getCompletions(
    projectId: number,
    language: string,
    filePath: string,
    line: number,
    character: number,
    content?: string
  ): Promise<CompletionItem[]> {
    try {
      const response = await api.post(
        `/lsp/${projectId}/completions?language=${language}`,
        {
          file_path: filePath,
          line,
          character,
          content
        }
      );

      return (response.data as any).completions || [];
    } catch (error) {
      console.error('LSP completions error:', error);
      return [];
    }
  }

  /**
   * Get diagnostics (errors, warnings).
   */
  async getDiagnostics(
    projectId: number,
    language: string,
    filePath: string,
    content?: string
  ): Promise<Diagnostic[]> {
    try {
      const response = await api.post(
        `/lsp/${projectId}/diagnostics?language=${language}`,
        {
          file_path: filePath,
          content
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
    try {
      const response = await api.post(
        `/lsp/${projectId}/hover?language=${language}`,
        {
          file_path: filePath,
          line,
          character,
          content
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
    try {
      const response = await api.post(
        `/lsp/${projectId}/definition?language=${language}`,
        {
          file_path: filePath,
          line,
          character,
          content
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
    try {
      await api.delete(`/lsp/${projectId}/shutdown?language=${language}`);

      const key = `${projectId}:${language}`;
      this.initialized.delete(key);

      console.log(`✓ LSP shutdown for ${language}`);
    } catch (error) {
      console.error(`LSP shutdown failed for ${language}:`, error);
    }
  }

  /**
   * Map file extension to language.
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
      'toml': 'rust', // Cargo.toml
      'go': 'go',
      'java': 'java',
      'c': 'c',
      'cpp': 'cpp',
      'cc': 'cpp',
      'cxx': 'cpp',
      'h': 'c',
      'hpp': 'cpp',
      'sql': 'sql',
      'sh': 'shell',
      'bash': 'shell'
    };

    return ext ? (languageMap[ext] || null) : null;
  }
}

export const lspService = new LSPService();
export default lspService;
