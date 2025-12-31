# Test Instructions: pylsp Hover Functionality

## Backend Status: ✅ Working
Backend pylsp renvoie correctement la documentation:
```bash
curl -X POST "http://localhost:8000/lsp/1/hover?language=python" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.py", "line": 1, "character": 7, "content": "import sys"}'
```
Returns full `sys` module documentation.

## Frontend Test Steps

### 1. Open Workspace
1. Navigate to http://localhost:3000/workspace/1
2. Wait for workspace to load
3. Open `test_pylsp_hover.py` from file explorer

### 2. Test Hover
**Test locations to hover:**

- Line 2: Hover over `sys` → Should show: "This module provides access to some objects..."
- Line 3: Hover over `os` → Should show: "OS routines for NT or Posix..."
- Line 4: Hover over `Path` → Should show: "PurePath subclass..."
- Line 6: Hover over `greet` → Should show function docstring
- Line 21: Hover over `version` → Should show sys.version documentation

### 3. Check Browser Console
Open DevTools (F12) and look for:
```
[HOVER DEBUG] Response: {...}
[HOVER DEBUG] Displaying: ...
```

If you see these logs → Frontend is working
If NO logs → Hover provider not triggered

### 4. Test Autocomplete
Type on a new line:
```python
sys.
```
Should show 84+ completions with documentation.

### 5. Expected Behavior
- **Hover delay**: 200ms
- **Visual**: Tooltip with markdown-formatted docs
- **Badge**: Green "LSP: python" indicator in top-right

## Troubleshooting

### If hover doesn't work:
1. Check console for `[HOVER DEBUG]` logs
2. Check Network tab for `/lsp/1/hover` requests
3. Verify LSP badge shows "LSP: python"
4. Try reloading workspace (F5)

### If badge is missing:
- Language detection failed
- Check file extension is .py
- Re-open the file

### If no autocomplete:
- Type `sys.` and wait
- Should trigger after `.`
- Check console for errors
