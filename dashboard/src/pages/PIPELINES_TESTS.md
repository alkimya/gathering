# Pipeline Tests Documentation

This document describes the test coverage for the Pipeline feature in the GatheRing dashboard.

## Overview

The Pipeline feature allows users to create visual workflows for multi-agent orchestration. Tests are organized across four files covering types, API, components, and pages.

## Test Files

### 1. Types Tests (`types/index.test.ts`)

Tests for TypeScript type definitions.

| Test | Description |
|------|-------------|
| `allows valid PipelineStatus values` | Validates `'active' \| 'paused' \| 'draft'` |
| `allows valid PipelineNodeType values` | Validates `'trigger' \| 'agent' \| 'condition' \| 'action' \| 'parallel' \| 'delay'` |
| `allows valid PipelineRunStatus values` | Validates `'pending' \| 'running' \| 'completed' \| 'failed' \| 'cancelled'` |
| `defines PipelineNode interface correctly` | Tests trigger node with config |
| `defines PipelineNode with agent config` | Tests agent node with task config |
| `defines PipelineEdge interface correctly` | Tests edge with condition |
| `defines Pipeline interface correctly` | Tests full pipeline structure |
| `defines PipelineRun interface correctly` | Tests run with logs |
| `defines PipelineRun with error state` | Tests failed run with error_message |

### 2. API Tests (`services/api.test.ts`)

Tests for the `pipelines` API service.

| Test | Endpoint | Description |
|------|----------|-------------|
| `lists all pipelines` | `GET /pipelines` | Fetches pipeline list |
| `lists pipelines by status` | `GET /pipelines?status=active` | Filters by status |
| `gets a pipeline by id` | `GET /pipelines/:id` | Fetches single pipeline |
| `creates a pipeline` | `POST /pipelines` | Creates new pipeline |
| `updates a pipeline` | `PUT /pipelines/:id` | Updates existing pipeline |
| `deletes a pipeline` | `DELETE /pipelines/:id` | Deletes pipeline |
| `toggles pipeline status` | `POST /pipelines/:id/toggle` | Toggles active/paused |
| `runs a pipeline` | `POST /pipelines/:id/run` | Triggers pipeline execution |
| `gets pipeline runs` | `GET /pipelines/:id/runs` | Lists execution history |
| `gets pipeline runs with filters` | `GET /pipelines/:id/runs?status=...` | Filtered history |
| `gets a specific run` | `GET /pipelines/:id/runs/:runId` | Single run details |
| `cancels a run` | `POST /pipelines/:id/runs/:runId/cancel` | Cancels running pipeline |

### 3. PipelineEditor Tests (`components/PipelineEditor.test.tsx`)

Tests for the visual pipeline editor component.

#### Rendering Tests
| Test | Description |
|------|-------------|
| `renders the editor for new pipeline with default name` | Shows "New Pipeline" input |
| `renders the editor for existing pipeline with its name` | Shows pipeline name |
| `renders pipeline nodes from existing pipeline` | Displays node cards |
| `renders Save Pipeline button` | Save button present |
| `renders Add Node button` | Add Node button present |

#### Interaction Tests
| Test | Description |
|------|-------------|
| `calls onClose when X button is clicked` | Close button triggers callback |
| `updates pipeline name when input changes` | Name input is editable |
| `opens node type dropdown when Add Node is clicked` | Shows Trigger, Agent, etc. |
| `calls onSave when Save Pipeline is clicked` | Save triggers callback with data |

#### Node Management Tests
| Test | Description |
|------|-------------|
| `shows default Start trigger node for new pipelines` | New pipeline has "Start" node |
| `adds a new agent node when Agent is selected` | Clicking Agent adds "New Agent" node |

### 4. Pipelines Page Tests (`pages/Pipelines.test.tsx`)

Tests for the main Pipelines page.

#### Rendering Tests
| Test | Description |
|------|-------------|
| `renders the page title` | Shows "Pipelines" heading |
| `renders stats cards` | Shows Total Pipelines stat |
| `renders pipeline cards` | Shows pipeline cards list |
| `renders filter buttons` | Shows All/Active/Paused/Draft filters |
| `renders New Pipeline button` | Shows create button |

#### Demo Data Fallback Tests
| Test | Description |
|------|-------------|
| `shows demo banner when API returns empty` | Shows "Demo Mode" banner |
| `shows demo pipelines when API returns empty` | Displays 3 demo pipelines |

#### Interaction Tests
| Test | Description |
|------|-------------|
| `opens pipeline editor when New Pipeline is clicked` | Opens editor modal |
| `runs a pipeline when Run Now is clicked` | Calls `pipelines.run()` |

#### Error Handling Tests
| Test | Description |
|------|-------------|
| `shows error state when API fails` | Shows "Failed to load pipelines" |
| `shows retry button on error` | Shows Retry button |

#### Pipeline Card Display Tests
| Test | Description |
|------|-------------|
| `shows pipeline status badge` | Shows active/paused badges |
| `shows run statistics` | Shows run count |
| `shows node preview in pipeline card` | Shows node names in card |

## Demo Pipeline Behavior

Demo pipelines have **negative IDs** (e.g., -1, -2, -3) to distinguish them from real pipelines.

### User Actions on Demo Pipelines

| Action | Behavior |
|--------|----------|
| **View Details** | Opens detail modal normally |
| **Edit** | Opens editor with demo content as template (name becomes "X (Copy)") |
| **Toggle** | Shows info toast: "This is a demo - create your own pipeline" |
| **Delete** | Shows info toast: "This is a demo - create your own pipeline" |
| **Run** | Shows info toast: "This is a demo - create your own pipeline to run it" |

### Save Logic

```typescript
// In handleSave:
if (editingPipeline && editingPipeline.id > 0) {
  // Update existing pipeline
  await updateMutation.mutateAsync({ id: editingPipeline.id, data });
} else {
  // Create new pipeline (including copies from demo templates with id=0)
  await createMutation.mutateAsync(data as { name: string });
}
```

When editing a demo pipeline:
1. The demo content is copied to the editor
2. The ID is set to `0` (not negative)
3. The name gets " (Copy)" suffix
4. On save, it creates a **new** pipeline (not update)

## Running Tests

```bash
# Run all tests
npm run test:run

# Run with coverage
npm run test:coverage

# Run specific test file
npm run test:run -- src/pages/Pipelines.test.tsx

# Run tests in watch mode
npm run test
```

## Current Coverage

| File | Statements | Branches | Functions | Lines |
|------|------------|----------|-----------|-------|
| PipelineEditor.tsx | 46.1% | 44.0% | 29.7% | 47.8% |
| Pipelines.tsx | 50.0% | 40.5% | 34.0% | 51.7% |

## Future Test Improvements

1. **Edge Connection Tests**: Test connecting nodes with edges
2. **Node Configuration Tests**: Test type-specific config panels
3. **Keyboard Navigation**: Test Escape to cancel connection mode
4. **Drag & Drop**: Test node positioning (if implemented)
5. **Filter Tests**: Test status filtering more thoroughly
6. **Pipeline Run History**: Test runs/logs tabs in detail modal
