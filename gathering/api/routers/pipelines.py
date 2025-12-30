"""
Pipelines API endpoints.
Manages automated multi-agent workflows.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from gathering.api.dependencies import (
    get_database_service,
    DatabaseService,
)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class PipelineNodeConfig(BaseModel):
    """Configuration for a pipeline node."""
    trigger_type: Optional[str] = None  # For trigger nodes
    event: Optional[str] = None
    cron: Optional[str] = None
    agent_id: Optional[str] = None  # For agent nodes
    task: Optional[str] = None
    condition: Optional[str] = None  # For condition nodes
    action: Optional[str] = None  # For action nodes
    recipients: Optional[List[str]] = None
    channel: Optional[str] = None


class PipelineNode(BaseModel):
    """A node in a pipeline."""
    id: str
    type: str = Field(..., description="Node type: trigger, agent, condition, action, parallel, delay")
    name: str
    config: PipelineNodeConfig = Field(default_factory=PipelineNodeConfig)
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})
    next: Optional[List[str]] = None


class PipelineEdge(BaseModel):
    """An edge connecting two nodes."""
    id: str
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    condition: Optional[str] = None

    class Config:
        populate_by_name = True


class PipelineCreate(BaseModel):
    """Schema for creating a pipeline."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    nodes: List[PipelineNode] = Field(default_factory=list)
    edges: List[PipelineEdge] = Field(default_factory=list)
    status: str = Field("draft", description="Pipeline status: active, paused, draft")


class PipelineUpdate(BaseModel):
    """Schema for updating a pipeline."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    nodes: Optional[List[PipelineNode]] = None
    edges: Optional[List[PipelineEdge]] = None
    status: Optional[str] = None


class PipelineRunCreate(BaseModel):
    """Schema for triggering a pipeline run."""
    trigger_data: Optional[dict] = Field(default_factory=dict, description="Input data for the run")


class PipelineLogEntry(BaseModel):
    """A log entry for a pipeline run."""
    timestamp: str
    node_id: str
    message: str
    level: str = "info"  # info, warn, error


class PipelineResponse(BaseModel):
    """Response schema for a pipeline."""
    id: int
    name: str
    description: Optional[str] = None
    status: str
    nodes: List[dict] = []
    edges: List[dict] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0


class PipelineRunResponse(BaseModel):
    """Response schema for a pipeline run."""
    id: int
    pipeline_id: int
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_node: Optional[str] = None
    logs: List[dict] = []
    trigger_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_seconds: int = 0


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _serialize_row(row: dict) -> dict:
    """Convert database row to JSON-serializable dict."""
    result = {}
    for key, value in row.items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        elif isinstance(value, (list, tuple)):
            result[key] = list(value) if value else []
        else:
            result[key] = value
    return result


def _ensure_table_exists(db: DatabaseService):
    """Ensure the pipelines tables exist."""
    # Pipelines table
    db.execute("""
        CREATE TABLE IF NOT EXISTS circle.pipelines (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('active', 'paused', 'draft')),
            nodes JSONB DEFAULT '[]'::jsonb,
            edges JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_run TIMESTAMP WITH TIME ZONE,
            run_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0
        )
    """)

    # Pipeline runs table
    db.execute("""
        CREATE TABLE IF NOT EXISTS circle.pipeline_runs (
            id SERIAL PRIMARY KEY,
            pipeline_id INTEGER NOT NULL REFERENCES circle.pipelines(id) ON DELETE CASCADE,
            status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            current_node VARCHAR(100),
            logs JSONB DEFAULT '[]'::jsonb,
            trigger_data JSONB DEFAULT '{}'::jsonb,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes if they don't exist
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_pipelines_status ON circle.pipelines(status);
        CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON circle.pipeline_runs(pipeline_id);
        CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON circle.pipeline_runs(status);
    """)


@router.get("", response_model=dict)
async def list_pipelines(
    status: Optional[str] = None,
    limit: int = 50,
    db: DatabaseService = Depends(get_database_service),
):
    """List all pipelines with optional status filter."""
    _ensure_table_exists(db)

    sql = "SELECT * FROM circle.pipelines WHERE 1=1"
    params = {}

    if status:
        sql += " AND status = %(status)s"
        params['status'] = status

    sql += " ORDER BY updated_at DESC LIMIT %(limit)s"
    params['limit'] = limit

    pipelines = db.execute(sql, params)
    pipelines = [_serialize_row(p) for p in pipelines]

    # Count by status
    counts = db.execute("""
        SELECT status, COUNT(*) as count
        FROM circle.pipelines
        GROUP BY status
    """)
    status_counts = {r['status']: r['count'] for r in counts}

    return {
        "pipelines": pipelines,
        "total": len(pipelines),
        "counts": status_counts,
    }


@router.get("/{pipeline_id}", response_model=dict)
async def get_pipeline(
    pipeline_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get details of a specific pipeline."""
    _ensure_table_exists(db)

    pipeline = db.execute_one("""
        SELECT * FROM circle.pipelines WHERE id = %(id)s
    """, {'id': pipeline_id})

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return _serialize_row(pipeline)


@router.post("", response_model=dict, status_code=201)
async def create_pipeline(
    data: PipelineCreate,
    db: DatabaseService = Depends(get_database_service),
):
    """Create a new pipeline."""
    _ensure_table_exists(db)

    import json
    nodes_json = json.dumps([n.model_dump() for n in data.nodes])
    edges_json = json.dumps([e.model_dump(by_alias=True) for e in data.edges])

    result = db.execute_one("""
        INSERT INTO circle.pipelines (name, description, status, nodes, edges)
        VALUES (%(name)s, %(description)s, %(status)s, %(nodes)s::jsonb, %(edges)s::jsonb)
        RETURNING *
    """, {
        'name': data.name,
        'description': data.description,
        'status': data.status,
        'nodes': nodes_json,
        'edges': edges_json,
    })

    return _serialize_row(result)


@router.put("/{pipeline_id}", response_model=dict)
async def update_pipeline(
    pipeline_id: int,
    data: PipelineUpdate,
    db: DatabaseService = Depends(get_database_service),
):
    """Update a pipeline."""
    _ensure_table_exists(db)

    # Check exists
    existing = db.execute_one(
        "SELECT id FROM circle.pipelines WHERE id = %(id)s",
        {'id': pipeline_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Build update query
    updates = []
    params = {'id': pipeline_id}

    if data.name is not None:
        updates.append("name = %(name)s")
        params['name'] = data.name

    if data.description is not None:
        updates.append("description = %(description)s")
        params['description'] = data.description

    if data.status is not None:
        updates.append("status = %(status)s")
        params['status'] = data.status

    if data.nodes is not None:
        import json
        updates.append("nodes = %(nodes)s::jsonb")
        params['nodes'] = json.dumps([n.model_dump() for n in data.nodes])

    if data.edges is not None:
        import json
        updates.append("edges = %(edges)s::jsonb")
        params['edges'] = json.dumps([e.model_dump(by_alias=True) for e in data.edges])

    if not updates:
        # Nothing to update
        return await get_pipeline(pipeline_id, db)

    updates.append("updated_at = CURRENT_TIMESTAMP")

    sql = f"UPDATE circle.pipelines SET {', '.join(updates)} WHERE id = %(id)s RETURNING *"
    result = db.execute_one(sql, params)

    return _serialize_row(result)


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(
    pipeline_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Delete a pipeline and all its runs."""
    _ensure_table_exists(db)

    # Check exists
    existing = db.execute_one(
        "SELECT id FROM circle.pipelines WHERE id = %(id)s",
        {'id': pipeline_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    db.execute(
        "DELETE FROM circle.pipelines WHERE id = %(id)s",
        {'id': pipeline_id}
    )


@router.post("/{pipeline_id}/toggle", response_model=dict)
async def toggle_pipeline(
    pipeline_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Toggle pipeline status between active and paused."""
    _ensure_table_exists(db)

    pipeline = db.execute_one(
        "SELECT status FROM circle.pipelines WHERE id = %(id)s",
        {'id': pipeline_id}
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    new_status = 'paused' if pipeline['status'] == 'active' else 'active'

    result = db.execute_one("""
        UPDATE circle.pipelines
        SET status = %(status)s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %(id)s
        RETURNING *
    """, {'id': pipeline_id, 'status': new_status})

    return _serialize_row(result)


# =============================================================================
# Pipeline Runs
# =============================================================================

@router.post("/{pipeline_id}/run", response_model=dict, status_code=201)
async def run_pipeline(
    pipeline_id: int,
    data: PipelineRunCreate = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Trigger a pipeline run."""
    _ensure_table_exists(db)

    # Get pipeline
    pipeline = db.execute_one(
        "SELECT * FROM circle.pipelines WHERE id = %(id)s",
        {'id': pipeline_id}
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if pipeline['status'] != 'active':
        raise HTTPException(
            status_code=400,
            detail=f"Cannot run pipeline in '{pipeline['status']}' status. Activate it first."
        )

    import json
    trigger_data = data.trigger_data if data else {}

    # Create run
    run = db.execute_one("""
        INSERT INTO circle.pipeline_runs (pipeline_id, status, started_at, trigger_data, logs)
        VALUES (%(pipeline_id)s, 'running', CURRENT_TIMESTAMP, %(trigger_data)s::jsonb, '[]'::jsonb)
        RETURNING *
    """, {
        'pipeline_id': pipeline_id,
        'trigger_data': json.dumps(trigger_data),
    })

    # Update pipeline stats
    db.execute("""
        UPDATE circle.pipelines
        SET run_count = run_count + 1, last_run = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = %(id)s
    """, {'id': pipeline_id})

    # TODO: Actually execute the pipeline nodes (async task)
    # For now, just mark as completed after a simulated run
    import json
    nodes = pipeline['nodes'] if isinstance(pipeline['nodes'], list) else json.loads(pipeline['nodes'] or '[]')

    logs = []
    for node in nodes:
        logs.append({
            'timestamp': datetime.utcnow().isoformat(),
            'node_id': node.get('id', 'unknown'),
            'message': f"Executed node: {node.get('name', 'Unnamed')}",
            'level': 'info',
        })

    # Complete the run
    result = db.execute_one("""
        UPDATE circle.pipeline_runs
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP, logs = %(logs)s::jsonb
        WHERE id = %(id)s
        RETURNING *
    """, {
        'id': run['id'],
        'logs': json.dumps(logs),
    })

    # Update success count
    db.execute("""
        UPDATE circle.pipelines
        SET success_count = success_count + 1
        WHERE id = %(id)s
    """, {'id': pipeline_id})

    return _serialize_row(result)


@router.get("/{pipeline_id}/runs", response_model=dict)
async def list_pipeline_runs(
    pipeline_id: int,
    status: Optional[str] = None,
    limit: int = 20,
    db: DatabaseService = Depends(get_database_service),
):
    """List runs for a pipeline."""
    _ensure_table_exists(db)

    # Verify pipeline exists
    pipeline = db.execute_one(
        "SELECT id FROM circle.pipelines WHERE id = %(id)s",
        {'id': pipeline_id}
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    sql = "SELECT * FROM circle.pipeline_runs WHERE pipeline_id = %(pipeline_id)s"
    params = {'pipeline_id': pipeline_id}

    if status:
        sql += " AND status = %(status)s"
        params['status'] = status

    sql += " ORDER BY created_at DESC LIMIT %(limit)s"
    params['limit'] = limit

    runs = db.execute(sql, params)

    # Calculate duration for each run
    results = []
    for run in runs:
        run_dict = _serialize_row(run)
        if run.get('started_at') and run.get('completed_at'):
            duration = (run['completed_at'] - run['started_at']).total_seconds()
            run_dict['duration_seconds'] = int(duration)
        else:
            run_dict['duration_seconds'] = 0
        results.append(run_dict)

    return {
        "runs": results,
        "total": len(results),
        "pipeline_id": pipeline_id,
    }


@router.get("/{pipeline_id}/runs/{run_id}", response_model=dict)
async def get_pipeline_run(
    pipeline_id: int,
    run_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get details of a specific pipeline run."""
    _ensure_table_exists(db)

    run = db.execute_one("""
        SELECT * FROM circle.pipeline_runs
        WHERE id = %(run_id)s AND pipeline_id = %(pipeline_id)s
    """, {'run_id': run_id, 'pipeline_id': pipeline_id})

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    result = _serialize_row(run)
    if run.get('started_at') and run.get('completed_at'):
        duration = (run['completed_at'] - run['started_at']).total_seconds()
        result['duration_seconds'] = int(duration)
    else:
        result['duration_seconds'] = 0

    return result


@router.post("/{pipeline_id}/runs/{run_id}/cancel", response_model=dict)
async def cancel_pipeline_run(
    pipeline_id: int,
    run_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Cancel a running pipeline execution."""
    _ensure_table_exists(db)

    run = db.execute_one("""
        SELECT status FROM circle.pipeline_runs
        WHERE id = %(run_id)s AND pipeline_id = %(pipeline_id)s
    """, {'run_id': run_id, 'pipeline_id': pipeline_id})

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run['status'] not in ('pending', 'running'):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel run in '{run['status']}' status"
        )

    result = db.execute_one("""
        UPDATE circle.pipeline_runs
        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
        WHERE id = %(run_id)s
        RETURNING *
    """, {'run_id': run_id})

    return _serialize_row(result)


# Export router
pipelines_router = router
