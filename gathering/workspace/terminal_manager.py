"""
Terminal Manager with PTY support.
Provides real terminal sessions for workspace.
"""

import asyncio
import os
import pty
import select
import subprocess
import termios
import struct
import fcntl
from typing import Optional, Dict
import shutil


class TerminalSession:
    """Manages a single PTY terminal session."""

    def __init__(self, project_path: str, session_id: str):
        self.project_path = project_path
        self.session_id = session_id
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.running = False

    def start(self) -> bool:
        """Start the terminal session."""
        try:
            # Fork PTY
            self.pid, self.master_fd = pty.fork()

            if self.pid == 0:  # Child process
                # Change to project directory
                try:
                    os.chdir(self.project_path)
                except Exception as e:
                    # If path doesn't exist, use home directory
                    os.chdir(os.path.expanduser('~'))

                # Detect shell
                shell = os.environ.get('SHELL', '/bin/bash')
                if not shutil.which(shell):
                    shell = '/bin/sh'  # Fallback

                # Set environment for better terminal experience
                os.environ['TERM'] = 'xterm-256color'
                os.environ['PS1'] = '\\[\\033[1;32m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[1;34m\\]\\w\\[\\033[00m\\]\\$ '

                # Execute shell
                os.execvp(shell, [shell])
            else:  # Parent process
                # Set non-blocking
                flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

                self.running = True
                print(f"Terminal session started: pid={self.pid}, fd={self.master_fd}")
                return True

        except Exception as e:
            print(f"Failed to start terminal: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def read(self) -> Optional[bytes]:
        """Read output from terminal (non-blocking)."""
        if not self.master_fd:
            return None

        try:
            # Check if data available
            r, _, _ = select.select([self.master_fd], [], [], 0.1)
            if r:
                data = os.read(self.master_fd, 1024)
                return data
        except (OSError, IOError):
            pass

        return None

    async def write(self, data: str) -> bool:
        """Write input to terminal."""
        if not self.master_fd:
            return False

        try:
            os.write(self.master_fd, data.encode('utf-8'))
            return True
        except (OSError, IOError) as e:
            print(f"Write error: {e}")
            return False

    def resize(self, rows: int, cols: int):
        """Resize terminal."""
        if not self.master_fd:
            return

        try:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception as e:
            print(f"Resize error: {e}")

    def stop(self):
        """Stop the terminal session."""
        self.running = False

        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass

        if self.pid:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0)
            except:
                pass


class TerminalManager:
    """Manages multiple terminal sessions."""

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}

    def create_session(self, project_path: str, session_id: str) -> TerminalSession:
        """Create a new terminal session."""
        session = TerminalSession(project_path, session_id)
        if session.start():
            self.sessions[session_id] = session
            return session
        raise Exception("Failed to create terminal session")

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get existing session."""
        return self.sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close a terminal session."""
        session = self.sessions.pop(session_id, None)
        if session:
            session.stop()


# Global manager instance
terminal_manager = TerminalManager()
