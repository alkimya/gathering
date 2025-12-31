# Phase 7.1 - Git Operations

## Overview

Added interactive Git operations to the Workspace Git View, allowing users to stage, commit, push, and pull directly from the UI.

## Features Implemented

### Backend (Python)

#### Git Manager Methods (`gathering/workspace/git_manager.py`)

1. **`stage_files(project_path, files)`**
   - Stage files for commit
   - Executes `git add` for each file
   - Returns success status with file list

2. **`unstage_files(project_path, files)`**
   - Unstage files
   - Executes `git restore --staged` for each file
   - Returns success status with file list

3. **`commit(project_path, message, author_name, author_email)`**
   - Create a commit with message
   - Optional author override
   - Returns commit hash and output
   - Validates message is not empty

4. **`push(project_path, remote, branch, set_upstream)`**
   - Push to remote repository
   - Default remote: "origin"
   - Optional upstream tracking (`-u` flag)
   - 30-second timeout
   - Returns status and output

5. **`pull(project_path, remote, branch)`**
   - Pull from remote repository
   - Default remote: "origin"
   - 30-second timeout
   - Returns status and output

#### API Endpoints (`gathering/api/routers/workspace.py`)

1. **POST `/workspace/{project_id}/git/stage`**
   - Body: `files: List[str]`
   - Stages specified files
   - Invalidates git status cache

2. **POST `/workspace/{project_id}/git/unstage`**
   - Body: `files: List[str]`
   - Unstages specified files
   - Invalidates git status cache

3. **POST `/workspace/{project_id}/git/commit`**
   - Body: `message: str`, `author_name?: str`, `author_email?: str`
   - Creates commit with message
   - Returns commit hash
   - Invalidates all git caches

4. **POST `/workspace/{project_id}/git/push`**
   - Body: `remote?: str`, `branch?: str`, `set_upstream?: bool`
   - Pushes to remote
   - Invalidates git status cache

5. **POST `/workspace/{project_id}/git/pull`**
   - Body: `remote?: str`, `branch?: str`
   - Pulls from remote
   - Invalidates all git caches

### Frontend (React/TypeScript)

#### GitActions Component (`dashboard/src/components/workspace/GitActions.tsx`)

**Features:**
- File selection with checkboxes
- Select/Deselect All functionality
- Visual file status indicators (modified, added, deleted, untracked)
- Stage selected files button
- Commit message textarea
- Commit button (validates message)
- Pull button (always enabled)
- Push button (shows ahead count, disabled if nothing to push)
- Success/error toast notifications
- Auto-refresh git status after operations
- Loading states for all operations

**UI States:**
1. **No Changes**: Shows only Push/Pull buttons
2. **With Changes**: Shows file list, stage, commit, and remote operations

**Color Coding:**
- Modified files: Blue
- Added files: Green
- Deleted files: Red
- Untracked files: Gray
- Stage button: Cyan
- Commit button: Green
- Pull button: Cyan
- Push button: Purple

#### Integration

GitActions is integrated into `GitStagingArea.tsx`:
- Replaces placeholder footer
- Receives `projectId`, `status`, and `onRefresh` callback
- Automatically refreshes status after operations

## User Flow

### Staging & Committing

1. User switches to **Status** tab in Git View
2. Sees list of changed files
3. Selects files to stage using checkboxes
4. Clicks "Stage Selected (N)" button
5. Enters commit message in textarea
6. Clicks "Commit" button
7. Git status automatically refreshes
8. Commit appears in Timeline/Graph

### Pushing & Pulling

1. After committing, Push button shows ahead count: "Push (N)"
2. Click "Push" to push commits to remote
3. Click "Pull" to pull latest changes from remote
4. Status refreshes automatically

## Error Handling

- Validates commit message not empty
- Displays API errors in red toast
- Shows success messages in green toast
- Handles git command failures gracefully
- 30-second timeout for push/pull operations

## Cache Invalidation

All operations invalidate appropriate caches:
- Stage/unstage: Invalidates status cache
- Commit: Invalidates all git caches (status, commits, graph)
- Push/pull: Invalidates all git caches

## Technical Details

### API Request Format

**Stage Files:**
```json
POST /workspace/1/git/stage
["file1.py", "file2.ts"]
```

**Commit:**
```json
POST /workspace/1/git/commit
{
  "message": "feat: add new feature",
  "author_name": "John Doe",
  "author_email": "john@example.com"
}
```

**Push:**
```json
POST /workspace/1/git/push
{
  "remote": "origin",
  "branch": "main",
  "set_upstream": false
}
```

**Pull:**
```json
POST /workspace/1/git/pull
{
  "remote": "origin",
  "branch": "main"
}
```

### Git Commands Executed

- Stage: `git add <file>`
- Unstage: `git restore --staged <file>`
- Commit: `git commit -m "<message>"`
- Push: `git push [-u] <remote> [<branch>]`
- Pull: `git pull <remote> [<branch>]`

## Build Metrics

- GitView bundle: 41.44 kB (gzipped: 8.82 kB)
- Build time: ~49s
- Total build successful

## Future Enhancements

Potential additions:
- Branch switching
- Branch creation/deletion
- Merge operations
- Rebase operations
- Stash management
- Cherry-pick
- Reset/revert
- Interactive staging (stage hunks)
- Commit history amendment
- Tag management

## Files Modified

### Backend
- `gathering/workspace/git_manager.py` - Added 5 new methods
- `gathering/api/routers/workspace.py` - Added 5 new endpoints

### Frontend
- `dashboard/src/components/workspace/GitActions.tsx` - New component (377 lines)
- `dashboard/src/components/workspace/GitStagingArea.tsx` - Integrated GitActions

## Testing

Manual testing recommended:
1. Stage files and verify they appear as staged
2. Create commit and verify it appears in Timeline/Graph
3. Push and verify remote receives commit
4. Pull and verify local updates with remote changes
5. Test error cases (empty message, push failures, etc.)

## User Request

Original request (French): "maintenant, la possibilité de commiter, de pousser et autres giteries"

Translation: "now, the ability to commit, push and other git operations"

✅ Implemented: Stage, unstage, commit, push, pull
