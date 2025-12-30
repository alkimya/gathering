#!/usr/bin/env python3
"""
Test script for WebSocket integration.

This script:
1. Starts a FastAPI server with WebSocket support
2. Connects a test client
3. Publishes events to Event Bus
4. Verifies WebSocket receives the events

Usage:
    python test_websocket_integration.py
"""

import asyncio
import websockets
import json
from datetime import datetime
from gathering.events import event_bus, Event, EventType
from gathering.websocket.integration import setup_websocket_broadcasting
from gathering.websocket import get_connection_manager


async def websocket_client():
    """Test WebSocket client that listens for events."""
    uri = "ws://localhost:8000/ws/dashboard?client_id=test-client"

    print(f"[Client] Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("[Client] ✅ Connected!")

            # Receive connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            print(f"[Client] Received: {data['type']}")

            # Listen for events (with timeout)
            print("[Client] Listening for events (10 seconds)...")

            event_count = 0
            try:
                while event_count < 5:  # Listen for 5 events
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    event_count += 1

                    print(f"[Client] Event #{event_count}: {data['type']}")
                    if 'data' in data:
                        print(f"         Data: {data['data']}")

            except asyncio.TimeoutError:
                print(f"[Client] Timeout after {event_count} events")

            print(f"[Client] ✅ Received {event_count} events total")

    except Exception as e:
        print(f"[Client] ❌ Error: {e}")
        print("[Client] Make sure the server is running:")
        print("         uvicorn gathering.api:app --reload")


async def publish_test_events():
    """Publish test events to Event Bus."""
    print("\n[Publisher] Publishing test events...")

    await asyncio.sleep(2)  # Give client time to connect

    # Event 1: Agent started
    await event_bus.publish(Event(
        type=EventType.AGENT_STARTED,
        data={
            "agent_id": 1,
            "name": "Alice",
            "competencies": ["python", "javascript"]
        },
        source_agent_id=1,
    ))
    print("[Publisher] ✅ Published: AGENT_STARTED")

    await asyncio.sleep(1)

    # Event 2: Task created
    await event_bus.publish(Event(
        type=EventType.TASK_CREATED,
        data={
            "task_id": 123,
            "title": "Build dashboard",
            "circle_id": 1
        },
        circle_id=1,
    ))
    print("[Publisher] ✅ Published: TASK_CREATED")

    await asyncio.sleep(1)

    # Event 3: Memory created
    await event_bus.publish(Event(
        type=EventType.MEMORY_CREATED,
        data={
            "content": "WebSocket integration works!",
            "agent_id": 1
        },
        source_agent_id=1,
    ))
    print("[Publisher] ✅ Published: MEMORY_CREATED")

    await asyncio.sleep(1)

    # Event 4: Task completed
    await event_bus.publish(Event(
        type=EventType.TASK_COMPLETED,
        data={
            "task_id": 123,
            "status": "success",
            "result": "Dashboard built successfully"
        },
        circle_id=1,
    ))
    print("[Publisher] ✅ Published: TASK_COMPLETED")

    await asyncio.sleep(1)

    # Event 5: Conversation message
    await event_bus.publish(Event(
        type=EventType.CONVERSATION_MESSAGE,
        data={
            "from_agent": 1,
            "to_agent": 2,
            "message": "Great work on the dashboard!"
        },
        source_agent_id=1,
    ))
    print("[Publisher] ✅ Published: CONVERSATION_MESSAGE")


async def test_local_manager():
    """Test ConnectionManager without running server."""
    print("\n=== Testing ConnectionManager (Local) ===\n")

    manager = get_connection_manager()

    # Get initial stats
    stats = manager.get_stats()
    print(f"[Manager] Active connections: {stats['active_connections']}")
    print(f"[Manager] Total connections: {stats['total_connections']}")
    print(f"[Manager] Total messages sent: {stats['total_messages_sent']}")
    print(f"[Manager] Total broadcasts: {stats['total_broadcasts']}")

    # Setup broadcasting
    setup_websocket_broadcasting()
    print("\n[Manager] ✅ WebSocket broadcasting enabled")

    # Publish a test event
    print("\n[Manager] Publishing test event...")
    await event_bus.publish(Event(
        type=EventType.AGENT_STARTED,
        data={"agent_id": 999, "name": "Test Agent"},
        source_agent_id=999,
    ))

    # Give time for event to process
    await asyncio.sleep(0.5)

    stats = manager.get_stats()
    print(f"[Manager] Broadcasts after event: {stats['total_broadcasts']}")

    print("\n[Manager] ✅ Local test complete")


async def test_with_server():
    """Test WebSocket with running server."""
    print("\n=== Testing WebSocket with Server ===\n")

    # Setup broadcasting on server side
    setup_websocket_broadcasting()
    print("[Server] WebSocket broadcasting enabled")

    # Start client and publisher concurrently
    await asyncio.gather(
        websocket_client(),
        publish_test_events(),
        return_exceptions=True
    )


async def main():
    """Main test function."""
    print("=" * 60)
    print("WebSocket Integration Test")
    print("=" * 60)

    # Test 1: Local manager (no server needed)
    await test_local_manager()

    print("\n" + "=" * 60)
    print("Ready for server test")
    print("=" * 60)
    print("\nTo test with server:")
    print("1. In terminal 1: uvicorn gathering.api:app --reload")
    print("2. In terminal 2: python test_websocket_integration.py server")
    print("\nOr run without arguments to test local manager only.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Test with server
        asyncio.run(test_with_server())
    else:
        # Test local only
        asyncio.run(main())
