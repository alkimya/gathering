# WebSocket

GatheRing uses WebSocket for real-time communication between the backend and clients.

## Overview

WebSocket channels:

| Channel | Purpose |
|---------|---------|
| `/ws/circles/{name}` | Circle events and messages |
| `/ws/workspace/{id}` | Workspace file/git updates |
| `/ws/agents/{id}` | Agent activity streams |

## Server Implementation

### Basic WebSocket Endpoint

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket):
        await websocket.accept()
        if channel not in self.connections:
            self.connections[channel] = set()
        self.connections[channel].add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket):
        if channel in self.connections:
            self.connections[channel].discard(websocket)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.connections:
            for connection in self.connections[channel]:
                await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/circles/{circle_name}")
async def circle_websocket(websocket: WebSocket, circle_name: str):
    await manager.connect(circle_name, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming message
            await handle_message(circle_name, data)
    except WebSocketDisconnect:
        manager.disconnect(circle_name, websocket)
```

### Message Types

```python
from enum import Enum
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class MessageType(str, Enum):
    # Circle events
    AGENT_MESSAGE = "agent_message"
    AGENT_JOINED = "agent_joined"
    AGENT_LEFT = "agent_left"
    CIRCLE_STATUS = "circle_status"

    # Workspace events
    FILE_CHANGED = "file_changed"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    GIT_STATUS = "git_status"

    # System events
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage(BaseModel):
    type: MessageType
    data: Any
    timestamp: datetime = datetime.utcnow()
    channel: Optional[str] = None
```

### Sending Messages

```python
async def send_agent_message(circle_name: str, agent_id: int, content: str):
    message = WebSocketMessage(
        type=MessageType.AGENT_MESSAGE,
        data={
            "agent_id": agent_id,
            "content": content,
        },
    )
    await manager.broadcast(circle_name, message.dict())
```

## Client Implementation

### JavaScript/TypeScript

```typescript
class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(private url: string) {}

  connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('Disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleMessage(message: any): void {
    switch (message.type) {
      case 'agent_message':
        this.onAgentMessage?.(message.data);
        break;
      case 'file_changed':
        this.onFileChanged?.(message.data);
        break;
      // ... handle other types
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
    }
  }

  send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect(): void {
    this.ws?.close();
  }

  // Event handlers
  onAgentMessage?: (data: any) => void;
  onFileChanged?: (data: any) => void;
}

// Usage
const client = new WebSocketClient('ws://localhost:8000/ws/circles/dev-team');
client.onAgentMessage = (data) => {
  console.log(`${data.agent_id}: ${data.content}`);
};
client.connect();
```

### React Hook

```typescript
import { useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);
    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  return { messages, isConnected, send };
}

// Usage in component
function CircleChat({ circleName }: { circleName: string }) {
  const { messages, isConnected, send } = useWebSocket(
    `ws://localhost:8000/ws/circles/${circleName}`
  );

  return (
    <div>
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      {messages.map((msg, i) => (
        <div key={i}>{msg.data.content}</div>
      ))}
    </div>
  );
}
```

### Python Client

```python
import asyncio
import websockets
import json


async def connect_to_circle(circle_name: str):
    uri = f"ws://localhost:8000/ws/circles/{circle_name}"

    async with websockets.connect(uri) as websocket:
        # Send a message
        await websocket.send(json.dumps({
            "type": "user_message",
            "content": "Hello, agents!",
        }))

        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")


# Run
asyncio.run(connect_to_circle("dev-team"))
```

## Event Bus Integration

WebSocket integrates with the Redis event bus:

```python
from gathering.events import EventBus

event_bus = EventBus()


@event_bus.subscribe("agent.message")
async def forward_to_websocket(event):
    """Forward agent messages to WebSocket clients."""
    circle_name = event["circle_name"]
    await manager.broadcast(circle_name, {
        "type": "agent_message",
        "data": event,
    })


@event_bus.subscribe("workspace.file_changed")
async def forward_file_change(event):
    """Forward file changes to workspace clients."""
    workspace_id = event["workspace_id"]
    await manager.broadcast(f"workspace-{workspace_id}", {
        "type": "file_changed",
        "data": event,
    })
```

## Authentication

### Token-based Auth

```python
from fastapi import WebSocket, Query, HTTPException

async def get_ws_user(token: str = Query(...)):
    user = await verify_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user


@router.websocket("/ws/circles/{name}")
async def circle_ws(
    websocket: WebSocket,
    name: str,
    token: str = Query(...),
):
    user = await get_ws_user(token)
    # ... continue with authenticated user
```

### Connection on First Message

```python
@router.websocket("/ws/circles/{name}")
async def circle_ws(websocket: WebSocket, name: str):
    await websocket.accept()

    # Wait for auth message
    auth_message = await websocket.receive_json()
    if auth_message.get("type") != "auth":
        await websocket.close(code=4001)
        return

    user = await verify_token(auth_message.get("token"))
    if not user:
        await websocket.close(code=4001)
        return

    # Now authenticated
    # ...
```

## Heartbeat/Keepalive

```python
import asyncio

async def heartbeat(websocket: WebSocket):
    """Send periodic pings to keep connection alive."""
    while True:
        try:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)
        except:
            break


@router.websocket("/ws/circles/{name}")
async def circle_ws(websocket: WebSocket, name: str):
    await manager.connect(name, websocket)

    # Start heartbeat
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "pong":
                continue  # Heartbeat response
            await handle_message(name, data)
    except WebSocketDisconnect:
        heartbeat_task.cancel()
        manager.disconnect(name, websocket)
```

## Testing WebSocket

```python
import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from gathering.api.app import app


def test_websocket_connect():
    client = TestClient(app)
    with client.websocket_connect("/ws/circles/test") as websocket:
        # Send message
        websocket.send_json({"type": "ping"})

        # Receive response
        data = websocket.receive_json()
        assert data["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_broadcast():
    client1 = TestClient(app)
    client2 = TestClient(app)

    with client1.websocket_connect("/ws/circles/test") as ws1:
        with client2.websocket_connect("/ws/circles/test") as ws2:
            # Send from client 1
            ws1.send_json({"type": "message", "content": "Hello"})

            # Receive on client 2
            data = ws2.receive_json()
            assert data["content"] == "Hello"
```

## Related Topics

- [Architecture](architecture.md) - System architecture
- [API](api.md) - REST API development
- [Testing](testing.md) - Testing guidelines
