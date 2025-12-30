# Event Bus - Real-Time Event System

The Event Bus provides a lightweight, type-safe event system for real-time communication between agents, circles, and system components in GatheRing.

## Overview

The Event Bus enables decoupled communication:
- **Agents** can publish events when completing tasks or executing tools
- **Circle members** can subscribe to circle events for coordination
- **Memory system** broadcasts shared knowledge automatically
- **Dashboard** can receive real-time updates via WebSocket

## Key Features

- ✅ **Simple API**: Subscribe, publish, done
- ✅ **Type-Safe**: Enum-based event types prevent typos
- ✅ **Async**: Concurrent handler execution for performance
- ✅ **Error Isolation**: One handler error doesn't affect others
- ✅ **Event History**: Track recent events for debugging
- ✅ **Filtering**: Subscribe only to relevant events
- ✅ **Testable**: Easy to mock and verify in tests

## Quick Start

```python
from gathering.events import event_bus, Event, EventType

# Subscribe to events
async def on_task_complete(event: Event):
    print(f"Task {event.data['task_id']} completed by agent {event.source_agent_id}")

event_bus.subscribe(EventType.TASK_COMPLETED, on_task_complete)

# Publish an event
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    data={"task_id": 123, "result": "success"},
    source_agent_id=1,
    circle_id=5,
))
```

## Event Types

Events are organized by domain:

### Agent Events
- `AGENT_STARTED` - Agent started processing
- `AGENT_STOPPED` - Agent stopped
- `AGENT_TASK_ASSIGNED` - Task assigned to agent
- `AGENT_TASK_COMPLETED` - Task completed successfully
- `AGENT_TASK_FAILED` - Task failed
- `AGENT_TOOL_EXECUTED` - Tool/skill executed

### Memory Events
- `MEMORY_CREATED` - New memory stored
- `MEMORY_SHARED` - Memory shared at circle/project scope
- `MEMORY_RECALLED` - Memory retrieved

### Circle Events
- `CIRCLE_CREATED` - Circle created
- `CIRCLE_STARTED` - Circle started
- `CIRCLE_STOPPED` - Circle stopped
- `CIRCLE_MEMBER_ADDED` - Member joined circle
- `CIRCLE_MEMBER_REMOVED` - Member left circle

### Task Events
- `TASK_CREATED` - New task created
- `TASK_ASSIGNED` - Task assigned to agent
- `TASK_STARTED` - Task started
- `TASK_COMPLETED` - Task completed
- `TASK_FAILED` - Task failed
- `TASK_CONFLICT_DETECTED` - Conflict detected (e.g., multiple agents modifying same file)

### Conversation Events
- `CONVERSATION_MESSAGE` - Message in conversation
- `CONVERSATION_TURN_COMPLETE` - Conversation turn complete

### System Events
- `SYSTEM_ERROR` - System error occurred
- `SYSTEM_WARNING` - System warning

## API Reference

### Event

```python
@dataclass
class Event:
    type: EventType                    # Event type
    data: Dict[str, Any]              # Event payload
    source_agent_id: Optional[int]    # Agent that triggered event
    circle_id: Optional[int]          # Circle context
    project_id: Optional[int]         # Project context
    timestamp: datetime               # When event occurred (auto-set)
    id: Optional[str]                 # Unique ID (auto-generated)
```

### EventBus

#### subscribe()

Subscribe to an event type:

```python
def subscribe(
    event_type: EventType,
    handler: Callable[[Event], Any],
    filter_fn: Optional[Callable[[Event], bool]] = None,
    name: Optional[str] = None,
) -> str
```

**Arguments:**
- `event_type`: Type of event to listen for
- `handler`: Async or sync function called when event occurs
- `filter_fn`: Optional filter (return True to receive event)
- `name`: Optional handler name for debugging

**Returns:** Subscription ID for unsubscribe

**Example:**
```python
# Subscribe to all task completions
event_bus.subscribe(EventType.TASK_COMPLETED, on_task_complete)

# Subscribe only to tasks in circle 1
event_bus.subscribe(
    EventType.TASK_COMPLETED,
    on_my_circle_task,
    filter_fn=lambda e: e.circle_id == 1
)
```

#### publish()

Publish an event:

```python
async def publish(event: Event) -> None
```

**Example:**
```python
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    data={"task_id": 123},
    source_agent_id=1,
))
```

#### get_history()

Get recent event history:

```python
def get_history(
    event_type: Optional[EventType] = None,
    limit: int = 100,
    **filters
) -> List[Event]
```

**Example:**
```python
# Get last 10 task completions
events = event_bus.get_history(EventType.TASK_COMPLETED, limit=10)

# Get circle 1 events
events = event_bus.get_history(circle_id=1)
```

## Integration Examples

### 1. Agent Coordination

Agents can coordinate their work via events:

```python
# Agent 1 completes a task
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    data={"task_id": 123, "output_file": "results.json"},
    source_agent_id=1,
    circle_id=5,
))

# Agent 2 listens for completed tasks
async def on_task_done(event: Event):
    if event.data.get("output_file"):
        # Process the output file
        await process_file(event.data["output_file"])

event_bus.subscribe(
    EventType.TASK_COMPLETED,
    on_task_done,
    filter_fn=lambda e: e.circle_id == 5  # Only circle 5
)
```

### 2. Knowledge Sharing

Memory system automatically broadcasts shared knowledge:

```python
from gathering.rag.memory_manager import MemoryManager

memory = MemoryManager.from_env()

# Agent 1 shares knowledge (automatically publishes MEMORY_SHARED event)
await memory.remember(
    agent_id=1,
    content="Database connection string is in .env.production",
    memory_type="decision",
    scope="circle",
    scope_id=5,
    importance=0.9,
)

# Agent 2 gets notified immediately
async def on_knowledge_shared(event: Event):
    print(f"New knowledge: {event.data['content']}")
    # Could trigger automatic indexing, notifications, etc.

event_bus.subscribe(EventType.MEMORY_SHARED, on_knowledge_shared)
```

### 3. Dashboard Real-Time Updates

Dashboard can show live activity:

```python
# In dashboard backend (WebSocket handler)
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()

    # Forward events to dashboard
    async def send_to_dashboard(event: Event):
        await websocket.send_json({
            "type": event.type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        })

    # Subscribe to relevant events
    event_bus.subscribe(EventType.TASK_COMPLETED, send_to_dashboard)
    event_bus.subscribe(EventType.MEMORY_SHARED, send_to_dashboard)
    event_bus.subscribe(EventType.AGENT_TOOL_EXECUTED, send_to_dashboard)

    # Keep connection alive
    while True:
        await websocket.receive_text()
```

### 4. Conflict Detection

Detect when multiple agents work on same file:

```python
file_locks = {}  # file_path -> agent_id

async def detect_conflicts(event: Event):
    if event.type == EventType.AGENT_TOOL_EXECUTED:
        tool = event.data.get("tool_name")
        if tool in ("fs_write", "fs_edit"):
            file_path = event.data["params"].get("path")
            if file_path in file_locks:
                # Conflict detected!
                await event_bus.publish(Event(
                    type=EventType.TASK_CONFLICT_DETECTED,
                    data={
                        "file_path": file_path,
                        "agent1_id": file_locks[file_path],
                        "agent2_id": event.source_agent_id,
                    },
                    circle_id=event.circle_id,
                ))
            else:
                file_locks[file_path] = event.source_agent_id

event_bus.subscribe(EventType.AGENT_TOOL_EXECUTED, detect_conflicts)
```

### 5. Automatic Task Assignment

Auto-assign tasks based on agent competencies:

```python
from gathering.orchestration.circle_store import CircleStore

store = CircleStore.from_env()

async def auto_assign_tasks(event: Event):
    if event.type == EventType.TASK_CREATED:
        task_id = event.data["task_id"]
        circle_id = event.data["circle_id"]
        required = set(event.data.get("required_competencies", []))

        # Find best agent
        members = store.list_members(circle_id)
        best_agent = None
        best_score = 0

        for member in members:
            competencies = set(member.get("competencies", []))
            score = len(required & competencies)
            if score > best_score:
                best_score = score
                best_agent = member["agent_id"]

        if best_agent:
            store.update_task_status(task_id, "pending", assigned_agent_id=best_agent)

event_bus.subscribe(EventType.TASK_CREATED, auto_assign_tasks)
```

## Current Integrations

The Event Bus is currently integrated in:

### AgentWrapper
- Publishes `AGENT_TOOL_EXECUTED` when tools are executed

### CircleStore
- Publishes `CIRCLE_CREATED` when circles are created
- Publishes `CIRCLE_MEMBER_ADDED` when members join
- Publishes `TASK_CREATED` when tasks are created
- Publishes `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED` when task status changes

### MemoryManager
- Publishes `MEMORY_SHARED` when memories are shared (circle/project scope)
- Publishes `MEMORY_CREATED` for private memories

## Performance Considerations

### Concurrent Execution

Handlers run concurrently for maximum performance:

```python
# These 3 handlers will run in parallel
event_bus.subscribe(EventType.TASK_COMPLETED, handler1)
event_bus.subscribe(EventType.TASK_COMPLETED, handler2)
event_bus.subscribe(EventType.TASK_COMPLETED, handler3)

# Publishing executes all 3 concurrently
await event_bus.publish(Event(type=EventType.TASK_COMPLETED))
```

### Error Isolation

Errors in one handler don't affect others:

```python
async def bad_handler(event: Event):
    raise ValueError("Oops!")  # This error is caught and logged

async def good_handler(event: Event):
    print("Still runs!")  # This still executes

event_bus.subscribe(EventType.TASK_COMPLETED, bad_handler)
event_bus.subscribe(EventType.TASK_COMPLETED, good_handler)
```

### Event History

Event history is limited to prevent memory growth:
- Default: 1000 most recent events
- Circular buffer (oldest events removed)
- Searchable by type and filters

```python
# Get last 10 events
recent = event_bus.get_history(limit=10)

# Clear history (useful for testing)
event_bus.clear_history()
```

## Testing

The Event Bus is designed to be testable:

```python
import pytest
from gathering.events import Event, EventType, event_bus

@pytest.mark.asyncio
async def test_my_feature():
    # Reset event bus
    event_bus.reset()

    # Track received events
    received = []

    async def track(event: Event):
        received.append(event)

    event_bus.subscribe(EventType.TASK_COMPLETED, track)

    # Trigger your feature
    await my_feature()

    # Verify events were published
    assert len(received) == 1
    assert received[0].type == EventType.TASK_COMPLETED
```

## Best Practices

### 1. Use Filters for Performance

Don't subscribe to everything if you only need specific events:

```python
# ❌ Bad - processes all events then filters
async def handler(event: Event):
    if event.circle_id != 5:
        return
    # Process...

# ✅ Good - filter at subscription level
event_bus.subscribe(
    EventType.TASK_COMPLETED,
    handler,
    filter_fn=lambda e: e.circle_id == 5
)
```

### 2. Keep Handlers Fast

Handlers run concurrently but should be fast:

```python
# ❌ Bad - blocks event bus
async def slow_handler(event: Event):
    await expensive_operation()  # 10 seconds

# ✅ Good - spawn background task
async def fast_handler(event: Event):
    asyncio.create_task(expensive_operation())
```

### 3. Use Type-Safe Event Data

Define event data structures for clarity:

```python
# ✅ Good - clear data structure
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    data={
        "task_id": 123,
        "result": "success",
        "duration_ms": 1234,
    }
))

# ❌ Bad - ambiguous data
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    data={"id": 123, "r": "ok", "d": 1234}
))
```

### 4. Clean Up Subscriptions

Unsubscribe when done:

```python
# Subscribe
sub_id = event_bus.subscribe(EventType.TASK_COMPLETED, handler)

# ... use it ...

# Clean up
event_bus.unsubscribe(sub_id)
```

## Roadmap

Future enhancements:

- [ ] **Persistent Events**: Store events in PostgreSQL for audit trail
- [ ] **Event Replay**: Replay past events for debugging
- [ ] **Event Schemas**: JSON Schema validation for event data
- [ ] **Rate Limiting**: Prevent event spam
- [ ] **Dead Letter Queue**: Handle failed event deliveries
- [ ] **Event Sourcing**: Full event-driven state management

## See Also

- [Architecture](ARCHITECTURE.md) - Overall system architecture
- [Circles](CIRCLES.md) - Circle collaboration
- [WebSocket Guide](WEBSOCKET.md) - Real-time dashboard updates (Phase 4)
