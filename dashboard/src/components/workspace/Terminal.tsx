/**
 * Terminal Component - xterm.js with WebSocket
 * Web3 Dark Theme Integration
 */

import { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { Terminal as TerminalIcon, X, Plus, Maximize2, Minimize2 } from 'lucide-react';

interface TerminalProps {
  projectId: number;
}

interface TerminalSession {
  id: string;
  terminal: XTerm;
  fitAddon: FitAddon;
  websocket: WebSocket | null;
}

export function Terminal({ projectId }: TerminalProps) {
  const terminalContainerRef = useRef<HTMLDivElement>(null);
  const [sessions, setSessions] = useState<TerminalSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('');
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    // Create first terminal on mount
    if (sessions.length === 0) {
      createTerminal();
    }

    return () => {
      // Cleanup all terminals on unmount
      sessions.forEach(session => {
        session.websocket?.close();
        session.terminal.dispose();
      });
    };
  }, []);

  useEffect(() => {
    // Fit terminal when window resizes
    const handleResize = () => {
      const activeSession = sessions.find(s => s.id === activeSessionId);
      if (activeSession) {
        try {
          activeSession.fitAddon.fit();
        } catch (e) {
          // Ignore fit errors
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [activeSessionId, sessions]);

  const createTerminal = () => {
    const sessionId = `term-${Date.now()}`;

    const terminal = new XTerm({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
      fontSize: 14,
      lineHeight: 1.2,
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#a855f7',
        cursorAccent: '#1e1e1e',
        selectionBackground: 'rgba(168, 85, 247, 0.3)',
        black: '#000000',
        red: '#ef4444',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#d4d4d4',
        brightBlack: '#71717a',
        brightRed: '#f87171',
        brightGreen: '#34d399',
        brightYellow: '#fbbf24',
        brightBlue: '#60a5fa',
        brightMagenta: '#c084fc',
        brightCyan: '#22d3ee',
        brightWhite: '#f4f4f5',
      },
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);

    // Create container for this terminal
    const container = document.createElement('div');
    container.style.display = activeSessionId === sessionId || sessions.length === 0 ? 'block' : 'none';
    container.style.width = '100%';
    container.style.height = '100%';

    if (terminalContainerRef.current) {
      terminalContainerRef.current.appendChild(container);
      terminal.open(container);

      // Fit after a short delay to ensure container is sized
      setTimeout(() => {
        try {
          fitAddon.fit();
        } catch (e) {
          console.warn('Terminal fit failed:', e);
        }
      }, 100);
    }

    // Connect WebSocket
    const wsUrl = `ws://localhost:8000/ws/terminal/${projectId}`;
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        terminal.writeln('\x1b[1;32m✓ Connected to terminal server\x1b[0m');
        terminal.writeln('');

        // Send initial terminal size
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'resize',
            rows: terminal.rows,
            cols: terminal.cols,
          }));
        }
      };

      ws.onmessage = (event) => {
        terminal.write(event.data);
      };

      ws.onerror = () => {
        terminal.writeln('\x1b[1;31m✗ WebSocket connection failed\x1b[0m');
        terminal.writeln('\x1b[90mTerminal server may not be running\x1b[0m');
      };

      ws.onclose = () => {
        terminal.writeln('\x1b[1;33m⚠ Connection closed\x1b[0m');
      };

      // Send terminal input to WebSocket
      terminal.onData((data) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'input', data }));
        }
      });
    } catch (error) {
      console.error('WebSocket error:', error);
      terminal.writeln('\x1b[1;31m✗ Failed to connect to terminal server\x1b[0m');
      terminal.writeln('\x1b[90mRunning in demo mode - commands will not execute\x1b[0m');
      terminal.writeln('');

      // Demo mode - echo input
      terminal.onData((data) => {
        if (data === '\r') {
          terminal.write('\r\n');
        } else if (data === '\x7F') { // Backspace
          terminal.write('\b \b');
        } else {
          terminal.write(data);
        }
      });
    }

    const newSession: TerminalSession = {
      id: sessionId,
      terminal,
      fitAddon,
      websocket: ws,
    };

    setSessions(prev => [...prev, newSession]);
    setActiveSessionId(sessionId);
  };

  const closeTerminal = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;

    console.log('Closing terminal:', sessionId);

    // Close WebSocket connection
    if (session.websocket) {
      try {
        session.websocket.close();
      } catch (e) {
        console.warn('Error closing websocket:', e);
      }
    }

    // Remove DOM element
    const container = terminalContainerRef.current;
    if (container && session.terminal.element?.parentElement) {
      try {
        container.removeChild(session.terminal.element.parentElement);
      } catch (e) {
        console.warn('Error removing terminal element:', e);
      }
    }

    // Dispose terminal instance
    try {
      session.terminal.dispose();
    } catch (e) {
      console.warn('Error disposing terminal:', e);
    }

    // Update sessions state
    const newSessions = sessions.filter(s => s.id !== sessionId);
    setSessions(newSessions);

    // Switch to another terminal if we closed the active one
    if (activeSessionId === sessionId && newSessions.length > 0) {
      setActiveSessionId(newSessions[0].id);
      // Show the new active terminal
      setTimeout(() => {
        const newActive = newSessions[0];
        if (newActive.terminal.element?.parentElement) {
          newActive.terminal.element.parentElement.style.display = 'block';
        }
      }, 0);
    }
  };

  const switchSession = (sessionId: string) => {
    // Hide all terminals
    sessions.forEach(session => {
      if (session.terminal.element?.parentElement) {
        session.terminal.element.parentElement.style.display = 'none';
      }
    });

    // Show selected terminal
    const session = sessions.find(s => s.id === sessionId);
    if (session && session.terminal.element?.parentElement) {
      session.terminal.element.parentElement.style.display = 'block';
      setActiveSessionId(sessionId);

      setTimeout(() => {
        try {
          session.fitAddon.fit();
        } catch (e) {
          // Ignore
        }
      }, 50);
    }
  };

  return (
    <div className={`flex flex-col ${isMaximized ? 'fixed inset-0 z-50 bg-[#1e1e1e]' : 'h-full'}`}>
      {/* Terminal tabs */}
      <div className="flex items-center gap-2 px-4 py-2 bg-[#252526] border-b border-white/5">
        <TerminalIcon className="w-4 h-4 text-cyan-400" />

        <div className="flex-1 flex items-center gap-1 overflow-x-auto">
          {sessions.map((session, index) => (
            <div
              key={session.id}
              className={`flex items-center gap-2 px-3 py-1 rounded-t transition-all cursor-pointer ${
                activeSessionId === session.id
                  ? 'bg-[#1e1e1e] text-white'
                  : 'bg-white/5 text-zinc-400 hover:bg-white/10'
              }`}
              onClick={() => switchSession(session.id)}
            >
              <span className="text-xs font-medium">Terminal {index + 1}</span>
              {sessions.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTerminal(session.id);
                  }}
                  className="p-0.5 hover:bg-white/10 rounded transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}

          <button
            onClick={createTerminal}
            className="p-1.5 hover:bg-white/10 rounded transition-colors text-zinc-400 hover:text-white"
            title="New Terminal"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={() => setIsMaximized(!isMaximized)}
          className="p-1.5 hover:bg-white/10 rounded transition-colors text-zinc-400 hover:text-white"
          title={isMaximized ? "Minimize" : "Maximize"}
        >
          {isMaximized ? (
            <Minimize2 className="w-4 h-4" />
          ) : (
            <Maximize2 className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Terminal container */}
      <div ref={terminalContainerRef} className="flex-1 bg-[#1e1e1e]" />
    </div>
  );
}
