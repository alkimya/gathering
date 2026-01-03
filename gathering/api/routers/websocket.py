"""
WebSocket router for real-time dashboard updates.

Provides:
- /ws/dashboard - Real-time event stream
- /ws/chat/{agent_id} - Streaming agent chat
- /ws/conversation/{conv_id} - Streaming multi-agent conversation
- Event broadcasting from Event Bus
- Connection management
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from gathering.websocket import get_connection_manager
from gathering.api.dependencies import get_agent_registry, get_circle_registry, get_conversation_registry, get_database_service
from gathering.agents.project_context import load_project_context

logger = logging.getLogger(__name__)

router = APIRouter()


def save_chat_message(agent_id: int, role: str, content: str, model_used: str = None, tokens_input: int = None, tokens_output: int = None) -> None:
    """Save a chat message to the database."""
    try:
        db = get_database_service()
        db._db.execute(
            """
            INSERT INTO communication.chat_history
            (agent_id, role, content, model_used, tokens_input, tokens_output, created_at)
            VALUES (%(agent_id)s, %(role)s, %(content)s, %(model_used)s, %(tokens_input)s, %(tokens_output)s, NOW())
            """,
            {"agent_id": agent_id, "role": role, "content": content, "model_used": model_used, "tokens_input": tokens_input, "tokens_output": tokens_output},
        )
    except Exception as e:
        logger.warning(f"Failed to save chat message: {e}")


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time dashboard updates.

    Clients connect to this endpoint to receive real-time events:
    - Agent task completions
    - Tool executions
    - Memory updates
    - Circle activity
    - System events

    Usage (JavaScript):
        const ws = new WebSocket('ws://localhost:8000/ws/dashboard?client_id=dashboard-1');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Event received:', data);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket closed');
        };

    Message format:
        {
            "type": "agent.task.completed",
            "data": {...},
            "timestamp": "2025-01-15T10:30:00Z"
        }

    Args:
        websocket: WebSocket connection
        client_id: Optional client identifier for tracking
    """
    manager = get_connection_manager()

    # Accept connection
    await manager.connect(websocket, client_id=client_id)

    try:
        # Send welcome message
        await manager.send_personal(
            {
                "type": "connection.established",
                "data": {
                    "client_id": client_id or f"client_{id(websocket)}",
                    "message": "Connected to GatheRing dashboard",
                },
            },
            websocket,
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (optional - for bidirectional comm)
                data = await websocket.receive_json()

                # Handle client messages (ping, subscribe filters, etc.)
                if data.get("type") == "ping":
                    await manager.send_personal(
                        {"type": "pong", "timestamp": data.get("timestamp")},
                        websocket,
                    )

                # Add more client message handling here as needed

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[WebSocket] Error receiving message: {e}")
                break

    finally:
        # Clean up on disconnect
        await manager.disconnect(websocket)


@router.get("/ws/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns:
        Connection stats including active connections and message counts.
    """
    manager = get_connection_manager()
    return manager.get_stats()


@router.websocket("/ws/chat/{agent_id}")
async def websocket_agent_chat(websocket: WebSocket, agent_id: int):
    """
    WebSocket endpoint for streaming agent chat responses.

    Protocol:
    1. Client sends: {"message": "Hello", "include_memories": true, "allow_tools": true}
    2. Server streams: {"type": "token", "content": "Hello"} (repeated)
    3. Server sends: {"type": "done", "content": "full response", "tokens_used": 123}
    4. On error: {"type": "error", "message": "error description"}

    Usage (JavaScript):
        const ws = new WebSocket(`ws://localhost:8000/ws/chat/${agentId}`);

        ws.onopen = () => {
            ws.send(JSON.stringify({ message: "Hello Sophie!" }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'token') {
                // Append token to response
                responseElement.textContent += data.content;
            } else if (data.type === 'done') {
                // Response complete
                console.log('Total tokens:', data.tokens_used);
            }
        };
    """
    await websocket.accept()

    # Get agent registry
    registry = get_agent_registry()
    agent = registry.get(agent_id)

    if not agent:
        await websocket.send_json({
            "type": "error",
            "message": f"Agent {agent_id} not found",
        })
        await websocket.close()
        return

    # Send connection established
    await websocket.send_json({
        "type": "connected",
        "agent_id": agent_id,
        "agent_name": agent.name,
    })

    try:
        while True:
            # Receive chat message from client
            data = await websocket.receive_json()

            message = data.get("message", "")
            if not message:
                await websocket.send_json({
                    "type": "error",
                    "message": "No message provided",
                })
                continue

            # Send start event
            await websocket.send_json({
                "type": "start",
                "agent_name": agent.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            try:
                allow_tools = data.get("allow_tools", True)

                # If tools are requested, use agent.chat() which handles tools properly
                # Streaming with tools is complex, so we fall back to non-streaming for tool use
                if allow_tools and agent._skills:
                    # Use agent.chat() for full tool support
                    response = await agent.chat(
                        message=message,
                        include_memories=data.get("include_memories", True),
                        allow_tools=True,
                    )

                    # Save to database
                    save_chat_message(agent_id, "user", message)
                    save_chat_message(agent_id, "assistant", response.content, tokens_output=response.tokens_used)

                    # Send response as chunked tokens for UI consistency
                    chunk_size = 50
                    for i in range(0, len(response.content), chunk_size):
                        chunk = response.content[i:i+chunk_size]
                        await websocket.send_json({
                            "type": "token",
                            "content": chunk,
                        })

                    # Send done event with tool info
                    await websocket.send_json({
                        "type": "done",
                        "content": response.content,
                        "agent_name": agent.name,
                        "tokens_used": response.tokens_used,
                        "tool_calls": response.tool_calls,
                        "tool_results": response.tool_results,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                # Check if LLM supports streaming (no tools mode)
                elif hasattr(agent.llm, 'stream'):
                    llm = agent.llm
                    # Build context for streaming
                    project_id = agent.get_project_id() if hasattr(agent, 'get_project_id') else None

                    # Load project context (default to GatheRing project)
                    project_context = None
                    if project_id:
                        project_context = load_project_context(project_id=project_id)
                    else:
                        # Default to GatheRing project for agents without explicit project
                        project_context = load_project_context(project_name="gathering")

                    # Cache project in memory service for system prompt building
                    if project_context and project_context.id:
                        agent.memory.set_project(project_context.id, project_context)

                    context = await agent.memory.build_context(
                        agent_id=agent.agent_id,
                        user_message=message,
                        project_id=project_context.id if project_context else None,
                        include_memories=data.get("include_memories", True),
                    )

                    # Build messages
                    messages = []
                    if context.system_prompt:
                        system_prompt = context.system_prompt
                    else:
                        # Build system prompt with project context
                        system_prompt = agent.persona.build_system_prompt(project_context)

                    messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": message})

                    # Stream response
                    full_response = ""
                    async for token in llm.stream(messages):
                        full_response += token
                        await websocket.send_json({
                            "type": "token",
                            "content": token,
                        })

                    # Update agent session
                    agent.session.add_message("user", message)
                    agent.session.add_message("assistant", full_response)

                    # Save to database
                    save_chat_message(agent_id, "user", message)
                    save_chat_message(agent_id, "assistant", full_response, tokens_output=len(full_response) // 4)

                    # Send done event
                    await websocket.send_json({
                        "type": "done",
                        "content": full_response,
                        "agent_name": agent.name,
                        "tokens_used": len(full_response) // 4,  # Approximate
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                else:
                    # Fallback to non-streaming
                    response = await agent.chat(
                        message=message,
                        include_memories=data.get("include_memories", True),
                        allow_tools=data.get("allow_tools", True),
                    )

                    # Save to database
                    save_chat_message(agent_id, "user", message)
                    save_chat_message(agent_id, "assistant", response.content, tokens_output=response.tokens_used)

                    # Send full response as single message
                    await websocket.send_json({
                        "type": "done",
                        "content": response.content,
                        "agent_name": agent.name,
                        "tokens_used": response.tokens_used,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except Exception as e:
                logger.error(f"Chat error for agent {agent_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for agent {agent_id}")
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.websocket("/ws/conversation/{conv_id}")
async def websocket_conversation(websocket: WebSocket, conv_id: str):
    """
    WebSocket endpoint for streaming multi-agent conversations.

    Protocol:
    1. Client sends: {"action": "advance", "prompt": "optional prompt"}
    2. Server streams agent responses with agent attribution
    3. Server sends turn completion events

    Message types:
    - {"type": "turn_start", "agent_id": 1, "agent_name": "Sophie", "turn": 1}
    - {"type": "token", "agent_id": 1, "content": "Hello"}
    - {"type": "turn_end", "agent_id": 1, "content": "full response", "turn": 1}
    - {"type": "conversation_complete", "turns_taken": 5, "summary": "..."}
    - {"type": "error", "message": "..."}

    Usage (JavaScript):
        const ws = new WebSocket(`ws://localhost:8000/ws/conversation/${convId}`);

        ws.onopen = () => {
            ws.send(JSON.stringify({ action: "advance" }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'turn_start') {
                // New agent speaking
                addAgentBubble(data.agent_name);
            } else if (data.type === 'token') {
                // Append token to current agent's bubble
                appendToCurrentBubble(data.content);
            } else if (data.type === 'turn_end') {
                // Turn complete
                finalizeBubble(data.content);
            }
        };
    """
    await websocket.accept()

    # Get conversation registry
    conv_registry = get_conversation_registry()
    circle_registry = get_circle_registry()

    conv = conv_registry.get(conv_id)
    if not conv:
        await websocket.send_json({
            "type": "error",
            "message": f"Conversation {conv_id} not found",
        })
        await websocket.close()
        return

    # Get the circle for this conversation
    circle_name = conv.get("circle_name")
    circle = circle_registry.get(circle_name) if circle_name else None

    if not circle:
        await websocket.send_json({
            "type": "error",
            "message": f"Circle '{circle_name}' not found for conversation",
        })
        await websocket.close()
        return

    # Send connection established
    await websocket.send_json({
        "type": "connected",
        "conv_id": conv_id,
        "topic": conv.get("topic", ""),
        "circle_name": circle_name,
        "participants": conv.get("participant_names", []),
        "turns_taken": conv.get("turns_taken", 0),
        "max_turns": conv.get("max_turns", 20),
    })

    try:
        while True:
            # Receive command from client
            data = await websocket.receive_json()
            action = data.get("action", "")

            if action == "advance":
                # Advance the conversation by one turn
                prompt = data.get("prompt")

                try:
                    # Get next agent to speak
                    current_turn = conv.get("turns_taken", 0)
                    agent_ids = conv.get("agent_ids", [])

                    if not agent_ids:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No agents in conversation",
                        })
                        continue

                    # Round-robin agent selection
                    agent_idx = current_turn % len(agent_ids)
                    next_agent_id = agent_ids[agent_idx]

                    # Get agent from circle
                    agent_handle = None
                    for agent in circle.agents:
                        if agent.id == next_agent_id:
                            agent_handle = agent
                            break

                    if not agent_handle:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Agent {next_agent_id} not found in circle",
                        })
                        continue

                    # Send turn start
                    await websocket.send_json({
                        "type": "turn_start",
                        "agent_id": agent_handle.id,
                        "agent_name": agent_handle.name,
                        "turn": current_turn + 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                    # Build conversation context from messages
                    messages = conv.get("messages", [])
                    context_parts = []
                    for msg in messages[-10:]:  # Last 10 messages
                        agent_name = msg.get("agent_name", "User")
                        content = msg.get("content", "")
                        context_parts.append(f"{agent_name}: {content}")

                    conversation_context = "\n".join(context_parts)

                    # Build prompt for agent
                    if prompt:
                        full_prompt = f"{conversation_context}\n\nUser: {prompt}\n\n{agent_handle.name}:"
                    else:
                        full_prompt = f"{conversation_context}\n\n{agent_handle.name}:"

                    # Generate response
                    if agent_handle.process_message:
                        response = await agent_handle.process_message(full_prompt)

                        # For now, send full response (streaming would require access to underlying LLM)
                        # Send as tokens for UI consistency
                        chunk_size = 20
                        for i in range(0, len(response), chunk_size):
                            chunk = response[i:i+chunk_size]
                            await websocket.send_json({
                                "type": "token",
                                "agent_id": agent_handle.id,
                                "content": chunk,
                            })

                        # Add message to conversation
                        new_message = {
                            "agent_id": agent_handle.id,
                            "agent_name": agent_handle.name,
                            "content": response,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        messages.append(new_message)

                        # Update conversation
                        conv_registry.update(conv_id, {
                            "messages": messages,
                            "turns_taken": current_turn + 1,
                        })

                        # Send turn end
                        await websocket.send_json({
                            "type": "turn_end",
                            "agent_id": agent_handle.id,
                            "agent_name": agent_handle.name,
                            "content": response,
                            "turn": current_turn + 1,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                        # Check if conversation is complete
                        max_turns = conv.get("max_turns", 20)
                        if current_turn + 1 >= max_turns:
                            await websocket.send_json({
                                "type": "conversation_complete",
                                "turns_taken": current_turn + 1,
                                "message_count": len(messages),
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Agent {agent_handle.name} cannot process messages",
                        })

                except Exception as e:
                    logger.error(f"Conversation advance error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })

            elif action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation {conv_id}")
    except Exception as e:
        logger.error(f"WebSocket error for conversation {conv_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
