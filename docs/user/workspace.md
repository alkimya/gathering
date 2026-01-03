# Workspace

The Workspace is GatheRing's integrated development environment. It provides a complete toolset for managing projects, editing code, and collaborating with AI agents.

## Overview

The workspace includes:

- **File Explorer**: Navigate and manage project files
- **Code Editor**: Monaco-based editor with syntax highlighting
- **Terminal**: Integrated terminal for command execution
- **Git Panel**: Visual git operations
- **Media Viewers**: Support for images, audio, video, PDF

## Accessing the Workspace

Navigate to: `http://localhost:3000/workspace/{workspace_id}`

For example: <http://localhost:3000/workspace/1>

## File Explorer

### Features

- Directory tree navigation
- File creation, renaming, deletion
- Drag and drop support
- Search within files
- File type icons

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New file |
| `Ctrl+Shift+N` | New folder |
| `F2` | Rename |
| `Delete` | Delete |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |

### Context Menu

Right-click on files/folders for options:

- Open
- Open to the Side
- Rename
- Delete
- Copy Path
- Copy Relative Path

## Code Editor

### Syntax Highlighting

Supported languages include:

- Python, JavaScript, TypeScript
- HTML, CSS, SCSS
- JSON, YAML, TOML
- Markdown, RST
- SQL, Shell scripts
- And many more...

### Editor Features

- Line numbers
- Code folding
- Minimap
- Bracket matching
- Auto-indentation
- Multiple cursors

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+F` | Find |
| `Ctrl+H` | Replace |
| `Ctrl+/` | Toggle comment |
| `Ctrl+D` | Select next occurrence |
| `Alt+Up/Down` | Move line |

### LSP Integration

The editor includes Language Server Protocol support for:

- **Python**: pylsp with pyright
- **TypeScript/JavaScript**: tsserver
- **Rust**: rust-analyzer

Features provided:

- Autocompletion
- Hover documentation
- Go to definition
- Find references
- Diagnostics/errors

## Terminal

### Features

- Full terminal emulation (xterm.js)
- Multiple terminal tabs
- Resizable panels
- Command history
- Copy/paste support

### Usage

1. Click the terminal icon or press `` Ctrl+` ``
2. Type commands as in a regular terminal
3. Use `Ctrl+C` to interrupt
4. Use `Ctrl+Shift+C` / `Ctrl+Shift+V` for copy/paste

### Terminal Sessions

```bash
# The terminal runs in the workspace directory
$ pwd
/home/user/project

# Run any command
$ npm install
$ python manage.py runserver
$ git status
```

## Git Integration

### Git Panel

The Git panel shows:

- Current branch
- Changed files (staged/unstaged)
- Commit history
- Remote status

### Operations

#### Viewing Status

The panel automatically shows:

- Modified files (M)
- Added files (A)
- Deleted files (D)
- Untracked files (U)

#### Staging Changes

- Click the `+` button next to a file to stage
- Click `-` to unstage
- Use "Stage All" for all changes

#### Committing

1. Stage your changes
2. Enter a commit message
3. Click "Commit"

#### Viewing Diffs

Click on a changed file to see the diff:

- Green: Added lines
- Red: Removed lines
- Yellow: Modified lines

#### Other Operations

- **Pull**: Fetch and merge remote changes
- **Push**: Push commits to remote
- **Branch**: Create or switch branches
- **Stash**: Save work in progress

## Media Viewers

### Image Viewer

Supports: PNG, JPG, GIF, SVG, WebP

Features:

- Zoom in/out
- Pan/drag
- Fit to window
- Actual size

### Audio Player

Supports: MP3, WAV, OGG, FLAC

Features:

- Play/pause
- Seek bar
- Volume control
- Waveform visualization

### Video Player

Supports: MP4, WebM, OGG

Features:

- Play/pause
- Seek bar
- Volume control
- Fullscreen mode
- Playback speed

### PDF Viewer

Features:

- Page navigation
- Zoom control
- Text search
- Thumbnail view

## Layout

### Panels

The workspace has resizable panels:

```
┌─────────────┬──────────────────────────┐
│             │                          │
│   File      │       Editor             │
│   Explorer  │                          │
│             │                          │
├─────────────┼──────────────────────────┤
│   Git       │       Terminal           │
│   Panel     │                          │
└─────────────┴──────────────────────────┘
```

### Resizing

- Drag panel borders to resize
- Double-click to collapse/expand
- Panels remember their size

### Themes

The editor supports themes:

- Light mode
- Dark mode
- High contrast

## API Endpoints

### Workspace Info

```bash
curl http://localhost:8000/workspace/1/info
```

### File Operations

```bash
# List files
curl http://localhost:8000/workspace/1/files

# Read file
curl http://localhost:8000/workspace/1/files/src/main.py

# Write file
curl -X PUT http://localhost:8000/workspace/1/files/src/main.py \
  -H "Content-Type: application/json" \
  -d '{"content": "print(\"Hello\")"}'

# Delete file
curl -X DELETE http://localhost:8000/workspace/1/files/src/old.py
```

### Git Operations

```bash
# Get status
curl http://localhost:8000/workspace/1/git/status

# Get commits
curl http://localhost:8000/workspace/1/git/commits

# Stage file
curl -X POST http://localhost:8000/workspace/1/git/stage \
  -d '{"files": ["src/main.py"]}'

# Commit
curl -X POST http://localhost:8000/workspace/1/git/commit \
  -d '{"message": "Add feature"}'
```

## WebSocket Streaming

Real-time updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/workspace/1');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'file_changed':
      // Handle file change
      break;
    case 'git_status':
      // Handle git update
      break;
    case 'terminal_output':
      // Handle terminal output
      break;
  }
};
```

## Best Practices

### 1. Use Keyboard Shortcuts

Learn the shortcuts for faster navigation.

### 2. Organize Files

Keep a clean project structure:

```
project/
├── src/
├── tests/
├── docs/
└── README.md
```

### 3. Commit Often

Make small, focused commits with clear messages.

### 4. Use the Terminal

The integrated terminal avoids context switching.

### 5. Review Diffs

Always review changes before committing.

## Related Topics

- [Circles](circles.md) - Agent collaboration
- [Agents](agents.md) - AI agents in the workspace
- [API Reference](../api/reference.md) - Complete API documentation
