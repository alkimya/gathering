"""
Extended tests for TerminalManager.

Covers basic functionality and structure tests for terminal management.
Note: Full PTY testing is skipped due to fork() complexity in test environment.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path

from gathering.workspace.terminal_manager import (
    TerminalSession,
    TerminalManager,
    terminal_manager,
)


class TestTerminalSession:
    """Test TerminalSession class structure and methods."""

    def test_session_initialization(self):
        """Test creating a terminal session object."""
        session = TerminalSession("/tmp/test", "test-session-1")

        assert session.project_path == "/tmp/test"
        assert session.session_id == "test-session-1"
        assert session.master_fd is None
        assert session.pid is None
        assert session.running is False

    def test_session_has_start_method(self):
        """Test that session has start method."""
        session = TerminalSession("/tmp", "test")
        assert hasattr(session, 'start')
        assert callable(session.start)

    def test_session_has_read_method(self):
        """Test that session has async read method."""
        session = TerminalSession("/tmp", "test")
        assert hasattr(session, 'read')
        assert callable(session.read)

    def test_session_has_write_method(self):
        """Test that session has async write method."""
        session = TerminalSession("/tmp", "test")
        assert hasattr(session, 'write')
        assert callable(session.write)

    def test_session_has_resize_method(self):
        """Test that session has resize method."""
        session = TerminalSession("/tmp", "test")
        assert hasattr(session, 'resize')
        assert callable(session.resize)

    def test_session_has_stop_method(self):
        """Test that session has stop method."""
        session = TerminalSession("/tmp", "test")
        assert hasattr(session, 'stop')
        assert callable(session.stop)

    def test_stop_without_starting(self):
        """Test that stop() can be called safely without starting."""
        session = TerminalSession("/tmp", "test")
        # Should not raise exception
        session.stop()
        assert session.running is False

    def test_resize_without_fd(self):
        """Test that resize() handles missing fd gracefully."""
        session = TerminalSession("/tmp", "test")
        # Should not raise exception
        session.resize(24, 80)

    @pytest.mark.asyncio
    async def test_read_without_fd(self):
        """Test that read() returns None without fd."""
        session = TerminalSession("/tmp", "test")
        result = await session.read()
        assert result is None

    @pytest.mark.asyncio
    async def test_write_without_fd(self):
        """Test that write() returns False without fd."""
        session = TerminalSession("/tmp", "test")
        result = await session.write("test")
        assert result is False


class TestTerminalManager:
    """Test TerminalManager class."""

    def test_manager_initialization(self):
        """Test creating a terminal manager."""
        manager = TerminalManager()
        assert hasattr(manager, 'sessions')
        assert isinstance(manager.sessions, dict)
        assert len(manager.sessions) == 0

    def test_manager_has_create_session_method(self):
        """Test that manager has create_session method."""
        manager = TerminalManager()
        assert hasattr(manager, 'create_session')
        assert callable(manager.create_session)

    def test_manager_has_get_session_method(self):
        """Test that manager has get_session method."""
        manager = TerminalManager()
        assert hasattr(manager, 'get_session')
        assert callable(manager.get_session)

    def test_manager_has_close_session_method(self):
        """Test that manager has close_session method."""
        manager = TerminalManager()
        assert hasattr(manager, 'close_session')
        assert callable(manager.close_session)

    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        manager = TerminalManager()
        session = manager.get_session("nonexistent")
        assert session is None

    def test_close_nonexistent_session(self):
        """Test closing a session that doesn't exist."""
        manager = TerminalManager()
        # Should not raise exception
        manager.close_session("nonexistent")

    @patch('gathering.workspace.terminal_manager.TerminalSession.start')
    def test_create_session_success_mock(self, mock_start):
        """Test creating a session with mocked start."""
        mock_start.return_value = True

        manager = TerminalManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            session = manager.create_session(tmpdir, "test-session")

            assert session is not None
            assert "test-session" in manager.sessions
            assert manager.sessions["test-session"] == session
            mock_start.assert_called_once()

    @patch('gathering.workspace.terminal_manager.TerminalSession.start')
    def test_create_session_failure_mock(self, mock_start):
        """Test creating a session that fails to start."""
        mock_start.return_value = False

        manager = TerminalManager()
        with pytest.raises(Exception, match="Failed to create terminal session"):
            manager.create_session("/tmp", "test-session")

    @patch('gathering.workspace.terminal_manager.TerminalSession.start')
    @patch('gathering.workspace.terminal_manager.TerminalSession.stop')
    def test_close_session_calls_stop(self, mock_stop, mock_start):
        """Test that closing a session calls stop()."""
        mock_start.return_value = True

        manager = TerminalManager()
        session = manager.create_session("/tmp", "test-session")

        manager.close_session("test-session")

        mock_stop.assert_called_once()
        assert "test-session" not in manager.sessions

    @patch('gathering.workspace.terminal_manager.TerminalSession.start')
    def test_multiple_sessions(self, mock_start):
        """Test managing multiple sessions."""
        mock_start.return_value = True

        manager = TerminalManager()
        session1 = manager.create_session("/tmp", "session-1")
        session2 = manager.create_session("/tmp", "session-2")

        assert len(manager.sessions) == 2
        assert manager.get_session("session-1") == session1
        assert manager.get_session("session-2") == session2

    @patch('gathering.workspace.terminal_manager.TerminalSession.start')
    @patch('gathering.workspace.terminal_manager.TerminalSession.stop')
    def test_close_one_of_multiple_sessions(self, mock_stop, mock_start):
        """Test closing one session while keeping others."""
        mock_start.return_value = True

        manager = TerminalManager()
        manager.create_session("/tmp", "session-1")
        manager.create_session("/tmp", "session-2")

        manager.close_session("session-1")

        assert len(manager.sessions) == 1
        assert "session-1" not in manager.sessions
        assert "session-2" in manager.sessions


class TestGlobalTerminalManager:
    """Test global terminal manager instance."""

    def test_global_instance_exists(self):
        """Test that global terminal manager exists."""
        assert terminal_manager is not None
        assert isinstance(terminal_manager, TerminalManager)

    def test_global_instance_has_sessions(self):
        """Test that global instance has sessions dict."""
        assert hasattr(terminal_manager, 'sessions')
        assert isinstance(terminal_manager.sessions, dict)

    def test_global_instance_methods_callable(self):
        """Test that global instance methods are callable."""
        assert callable(terminal_manager.create_session)
        assert callable(terminal_manager.get_session)
        assert callable(terminal_manager.close_session)


class TestTerminalSessionWithMocks:
    """Test TerminalSession with mocked system calls."""

    @patch('gathering.workspace.terminal_manager.pty.fork')
    @patch('gathering.workspace.terminal_manager.fcntl.fcntl')
    def test_start_success_parent_process(self, mock_fcntl, mock_fork):
        """Test starting a session (parent process path)."""
        # Mock fork to return as parent process
        mock_fork.return_value = (1234, 5)  # (pid, master_fd)

        with tempfile.TemporaryDirectory() as tmpdir:
            session = TerminalSession(tmpdir, "test")
            result = session.start()

            assert result is True
            assert session.pid == 1234
            assert session.master_fd == 5
            assert session.running is True

    @patch('gathering.workspace.terminal_manager.pty.fork')
    def test_start_failure_exception(self, mock_fork):
        """Test starting a session that fails."""
        # Mock fork to raise exception
        mock_fork.side_effect = OSError("Fork failed")

        session = TerminalSession("/tmp", "test")
        result = session.start()

        assert result is False
        assert session.running is False

    @patch('gathering.workspace.terminal_manager.os.write')
    @pytest.mark.asyncio
    async def test_write_success(self, mock_write):
        """Test writing to terminal."""
        session = TerminalSession("/tmp", "test")
        session.master_fd = 5  # Set a fake fd

        result = await session.write("hello")

        assert result is True
        mock_write.assert_called_once_with(5, b"hello")

    @patch('gathering.workspace.terminal_manager.os.write')
    @pytest.mark.asyncio
    async def test_write_failure(self, mock_write):
        """Test write failure handling."""
        mock_write.side_effect = OSError("Write failed")

        session = TerminalSession("/tmp", "test")
        session.master_fd = 5

        result = await session.write("hello")

        assert result is False

    @patch('gathering.workspace.terminal_manager.select.select')
    @patch('gathering.workspace.terminal_manager.os.read')
    @pytest.mark.asyncio
    async def test_read_with_data(self, mock_read, mock_select):
        """Test reading data from terminal."""
        # Mock select to indicate data available
        mock_select.return_value = ([5], [], [])
        mock_read.return_value = b"output data"

        session = TerminalSession("/tmp", "test")
        session.master_fd = 5

        result = await session.read()

        assert result == b"output data"
        mock_read.assert_called_once_with(5, 1024)

    @patch('gathering.workspace.terminal_manager.select.select')
    @pytest.mark.asyncio
    async def test_read_no_data(self, mock_select):
        """Test reading when no data available."""
        # Mock select to indicate no data
        mock_select.return_value = ([], [], [])

        session = TerminalSession("/tmp", "test")
        session.master_fd = 5

        result = await session.read()

        assert result is None

    @patch('gathering.workspace.terminal_manager.fcntl.ioctl')
    def test_resize_success(self, mock_ioctl):
        """Test resizing terminal."""
        session = TerminalSession("/tmp", "test")
        session.master_fd = 5

        session.resize(30, 100)

        # Should have called ioctl
        assert mock_ioctl.called

    @patch('gathering.workspace.terminal_manager.fcntl.ioctl')
    def test_resize_failure(self, mock_ioctl):
        """Test resize failure handling."""
        mock_ioctl.side_effect = Exception("Resize failed")

        session = TerminalSession("/tmp", "test")
        session.master_fd = 5

        # Should not raise exception
        session.resize(30, 100)

    @patch('gathering.workspace.terminal_manager.os.close')
    @patch('gathering.workspace.terminal_manager.os.kill')
    @patch('gathering.workspace.terminal_manager.os.waitpid')
    def test_stop_cleanup(self, mock_waitpid, mock_kill, mock_close):
        """Test that stop() performs cleanup."""
        session = TerminalSession("/tmp", "test")
        session.master_fd = 5
        session.pid = 1234
        session.running = True

        session.stop()

        assert session.running is False
        mock_close.assert_called_once_with(5)
        mock_kill.assert_called_once_with(1234, 9)
        mock_waitpid.assert_called_once_with(1234, 0)

    @patch('gathering.workspace.terminal_manager.os.close')
    @patch('gathering.workspace.terminal_manager.os.kill')
    def test_stop_handles_errors(self, mock_kill, mock_close):
        """Test that stop() handles cleanup errors gracefully."""
        mock_close.side_effect = OSError("Close failed")
        mock_kill.side_effect = OSError("Kill failed")

        session = TerminalSession("/tmp", "test")
        session.master_fd = 5
        session.pid = 1234

        # Should not raise exception
        session.stop()
        assert session.running is False
