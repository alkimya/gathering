# Testing pylsp Hover & Autocomplete

## ✅ Backend Verified Working

```bash
# Backend pylsp returns full documentation
curl -X POST "http://localhost:8000/lsp/1/hover?language=python" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.py", "line": 1, "character": 7, "content": "import sys"}'

# Returns: Full sys module documentation (3.7KB)
```

## 🧪 Frontend Testing Steps

### 1. Access Workspace
```
http://localhost:3000/workspace/1
```

### 2. Open Test File
Click on `test_pylsp_hover.py` in the file explorer

### 3. Check Console Logs
Open Browser DevTools (F12) → Console tab

**Expected logs:**
```
✓ Setting up LSP providers for python file: test_pylsp_hover.py
✓ Hover provider registered for python
```

### 4. Test Hover (Mouse over code)

**Hover targets:**

| Line | Code | Expected Documentation |
|------|------|------------------------|
| 2 | `sys` | "This module provides access to some objects used or maintained by the interpreter..." |
| 3 | `os` | "OS routines for NT or Posix..." |
| 4 | `Path` | "PurePath subclass that can make system calls" |
| 6 | `greet` | Function docstring: "Greet someone with a friendly message..." |
| 21 | `version` | "sys.version documentation" |

**Console logs when hovering:**
```
[HOVER] Triggered at line X, col Y
[HOVER] Requesting hover for test_pylsp_hover.py at X:Y
[HOVER] Backend response: {contents: {...}}
[HOVER] ✓ Displaying documentation (XXX chars)
```

### 5. Test Autocomplete

Type on a new line:
```python
sys.
```

**Expected:**
- Dropdown appears after typing `.`
- Shows 84+ completions
- Each item has documentation preview

**Console logs:**
```
Completion request: projectId=1, language=python, filePath=test_pylsp_hover.py
```

### 6. Visual Indicators

**LSP Badge (top-right of editor):**
```
LSP: python [green indicator]
```

## 🐛 Troubleshooting

### Hover doesn't appear

**Check console for:**
```
[HOVER] Triggered at line X, col Y
```

- ✅ **If you see this:** Provider is registered, Monaco is triggering
- ❌ **If you don't:** Hover provider not being called

**If not triggered:**
1. Monaco settings might disable hover
2. Hover delay might be too long
3. Check editor focus

### Hover triggered but no tooltip

**Check console for:**
```
[HOVER] Backend response: ...
```

- ✅ **If you see response with content:** Backend works, display issue
- ❌ **If empty response:** Backend issue

**If backend returns null:**
- Position might be wrong (0-indexed vs 1-indexed)
- File content not synced
- pylsp not finding symbol

### LSP badge missing

- Language not detected (file must be `.py`)
- LSP initialization failed
- Check console for errors

## 📝 Current Implementation Status

### ✅ Working:
- Backend pylsp with Jedi
- Completions (84 items for `sys.`)
- Diagnostics (ruff/pyflakes)
- Hover backend (returns full docs)

### 🔍 Testing:
- Frontend hover display
- Monaco tooltip rendering
- Hover debounce (200ms)

### 📋 Test File Content

```python
"""Test file for pylsp hover functionality."""
import sys
import os
from pathlib import Path

def greet(name: str) -> str:
    """
    Greet someone with a friendly message.

    Args:
        name: The person's name to greet

    Returns:
        A greeting string
    """
    return f"Hello, {name}!"

# Hover over 'sys' should show module documentation
print(sys.version)

# Hover over 'greet' should show the docstring
result = greet("World")

# Hover over 'Path' should show pathlib documentation
home = Path.home()
```

## 🎯 Success Criteria

1. ✅ Console shows `[HOVER] Triggered` when hovering
2. ✅ Console shows `[HOVER] Backend response` with content
3. ✅ Console shows `[HOVER] ✓ Displaying documentation`
4. ✅ Visual tooltip appears with formatted documentation
5. ✅ Autocomplete works with documentation previews
6. ✅ LSP badge shows "LSP: python" in green

## 🚀 Next Steps After Testing

If hover still doesn't work:
1. Check Monaco Editor options (`hover.enabled`)
2. Try different Monaco version
3. Check if MarkdownString is needed instead of plain value
4. Verify content format (markdown vs plain text)

If it works:
1. Remove debug console.logs
2. Test with other languages (Rust, TypeScript)
3. Document in WORKSPACE_FIX.md
