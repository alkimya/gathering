"""
Conversation and collaboration endpoints.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from gathering.api.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessageSchema,
    ConversationStatus,
)
from gathering.api.dependencies import (
    get_circle_registry,
    get_conversation_registry,
    CircleRegistry,
    ConversationRegistry,
)
from gathering.agents import (
    AgentConversation,
    TurnStrategy,
    ConversationStatus as AgentConversationStatus,
)
from gathering.api.websocket import ws_manager, emit_conversation_event


router = APIRouter(prefix="/conversations", tags=["conversations"])


def _conv_status_to_api(status: AgentConversationStatus) -> ConversationStatus:
    """Convert agent conversation status to API status."""
    mapping = {
        AgentConversationStatus.PENDING: ConversationStatus.PENDING,
        AgentConversationStatus.ACTIVE: ConversationStatus.ACTIVE,
        AgentConversationStatus.COMPLETED: ConversationStatus.COMPLETED,
        AgentConversationStatus.CANCELLED: ConversationStatus.CANCELLED,
    }
    return mapping.get(status, ConversationStatus.PENDING)


def _conv_to_response(conv_data: dict) -> ConversationResponse:
    """Convert conversation data to response."""
    return ConversationResponse(
        id=conv_data["id"],
        topic=conv_data["topic"],
        status=conv_data.get("status", ConversationStatus.PENDING),
        participant_names=conv_data.get("participant_names", []),
        turns_taken=conv_data.get("turns_taken", 0),
        max_turns=conv_data.get("max_turns", 10),
        started_at=conv_data.get("started_at"),
        completed_at=conv_data.get("completed_at"),
    )


def _conv_to_detail(conv_data: dict) -> ConversationDetailResponse:
    """Convert conversation data to detailed response."""
    messages = []
    for msg in conv_data.get("messages", []):
        messages.append(ConversationMessageSchema(
            agent_id=msg["agent_id"],
            agent_name=msg["agent_name"],
            content=msg["content"],
            mentions=msg.get("mentions", []),
            timestamp=msg.get("timestamp", datetime.now(timezone.utc)),
        ))

    return ConversationDetailResponse(
        id=conv_data["id"],
        topic=conv_data["topic"],
        status=conv_data.get("status", ConversationStatus.PENDING),
        participant_names=conv_data.get("participant_names", []),
        turns_taken=conv_data.get("turns_taken", 0),
        max_turns=conv_data.get("max_turns", 10),
        started_at=conv_data.get("started_at"),
        completed_at=conv_data.get("completed_at"),
        messages=messages,
        transcript=conv_data.get("transcript", ""),
        summary=conv_data.get("summary"),
        duration_seconds=conv_data.get("duration_seconds", 0),
    )


# =============================================================================
# Conversation Endpoints
# =============================================================================


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    registry: ConversationRegistry = Depends(get_conversation_registry),
) -> ConversationListResponse:
    """List all conversations."""
    conversations = registry.list_all()
    return ConversationListResponse(
        conversations=[_conv_to_response(c) for c in conversations],
        total=len(conversations),
    )


@router.post("", response_model=ConversationDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    circle_name: str = "default",
    circle_registry: CircleRegistry = Depends(get_circle_registry),
    conv_registry: ConversationRegistry = Depends(get_conversation_registry),
) -> ConversationDetailResponse:
    """
    Start a new conversation between agents.

    Uses the GatheringCircle.collaborate() method to start
    a structured conversation between the specified agents.
    """
    circle = circle_registry.get(circle_name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{circle_name}' not found. Create a circle first.",
        )

    if circle.status.value != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Circle must be running to start conversations",
        )

    # Validate agent IDs
    for agent_id in data.agent_ids:
        if agent_id not in circle.agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent {agent_id} not found in circle '{circle_name}'",
            )

    # Store conversation data
    participant_names = [circle.agents[aid].name for aid in data.agent_ids]
    conv_data = {
        "topic": data.topic,
        "agent_ids": data.agent_ids,
        "participant_names": participant_names,
        "max_turns": data.max_turns,
        "initial_prompt": data.initial_prompt,
        "turn_strategy": data.turn_strategy,
        "circle_name": circle_name,
        "status": ConversationStatus.PENDING,
        "turns_taken": 0,
        "messages": [],
        "transcript": "",
        "started_at": None,
        "completed_at": None,
        "duration_seconds": 0,
    }

    conv_id = conv_registry.add(conv_data)

    return _conv_to_detail(conv_registry.get(conv_id))


@router.get("/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conv_id: str,
    registry: ConversationRegistry = Depends(get_conversation_registry),
) -> ConversationDetailResponse:
    """Get conversation details."""
    conv_data = registry.get(conv_id)
    if not conv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )
    return _conv_to_detail(conv_data)


@router.post("/{conv_id}/start", response_model=ConversationDetailResponse)
async def start_conversation(
    conv_id: str,
    circle_registry: CircleRegistry = Depends(get_circle_registry),
    conv_registry: ConversationRegistry = Depends(get_conversation_registry),
) -> ConversationDetailResponse:
    """
    Start a pending conversation.

    This executes the conversation using GatheringCircle.collaborate().
    """
    conv_data = conv_registry.get(conv_id)
    if not conv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )

    if conv_data["status"] != ConversationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversation is in {conv_data['status']} status, cannot start",
        )

    circle = circle_registry.get(conv_data["circle_name"])
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{conv_data['circle_name']}' not found",
        )

    # Update status
    conv_registry.update(conv_id, {
        "status": ConversationStatus.ACTIVE,
        "started_at": datetime.now(timezone.utc),
    })

    try:
        # Run the collaboration
        result = await circle.collaborate(
            topic=conv_data["topic"],
            agent_ids=conv_data["agent_ids"],
            max_turns=conv_data["max_turns"],
            initial_prompt=conv_data.get("initial_prompt", ""),
        )

        # Build messages list - start with user's initial message if present
        messages = []
        transcript_lines = []
        initial_prompt = conv_data.get("initial_prompt", "")
        if initial_prompt:
            user_ts = conv_data.get("started_at") or datetime.now(timezone.utc)
            messages.append({
                "agent_id": 0,
                "agent_name": "User",
                "content": initial_prompt,
                "mentions": [],
                "timestamp": user_ts,
            })
            transcript_lines.append(f"**User**: {initial_prompt}")

            # Broadcast user message
            await emit_conversation_event(conv_id, "message", {
                "agent_id": 0,
                "agent_name": "User",
                "content": initial_prompt,
                "timestamp": user_ts.isoformat() if hasattr(user_ts, 'isoformat') else str(user_ts),
            })

        # Add agent messages and broadcast each one
        for msg in result.messages:
            messages.append({
                "agent_id": msg.agent_id,
                "agent_name": msg.agent_name,
                "content": msg.content,
                "mentions": msg.mentions,
                "timestamp": msg.timestamp,
            })
            # Build transcript from messages
            transcript_lines.append(f"**{msg.agent_name}**: {msg.content}")

            # Broadcast agent message
            await emit_conversation_event(conv_id, "message", {
                "agent_id": msg.agent_id,
                "agent_name": msg.agent_name,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp),
            })

        transcript = "\n\n".join(transcript_lines)

        conv_registry.update(conv_id, {
            "status": ConversationStatus.COMPLETED,
            "completed_at": datetime.now(timezone.utc),
            "turns_taken": result.turns_taken,
            "messages": messages,
            "transcript": transcript,
            "summary": result.summary,
            "duration_seconds": result.duration_seconds,
        })

    except Exception as e:
        conv_registry.update(conv_id, {
            "status": ConversationStatus.CANCELLED,
            "completed_at": datetime.now(timezone.utc),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation failed: {str(e)}",
        )

    return _conv_to_detail(conv_registry.get(conv_id))


@router.post("/{conv_id}/cancel")
async def cancel_conversation(
    conv_id: str,
    registry: ConversationRegistry = Depends(get_conversation_registry),
):
    """Cancel a conversation."""
    conv_data = registry.get(conv_id)
    if not conv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )

    if conv_data["status"] in (ConversationStatus.COMPLETED, ConversationStatus.CANCELLED):
        return {"status": "already_finished"}

    registry.update(conv_id, {
        "status": ConversationStatus.CANCELLED,
        "completed_at": datetime.now(timezone.utc),
    })

    return {"status": "cancelled"}


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conv_id: str,
    registry: ConversationRegistry = Depends(get_conversation_registry),
):
    """Delete a conversation."""
    if not registry.remove(conv_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )


@router.get("/{conv_id}/transcript")
async def get_transcript(
    conv_id: str,
    registry: ConversationRegistry = Depends(get_conversation_registry),
):
    """Get conversation transcript as plain text."""
    conv_data = registry.get(conv_id)
    if not conv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )

    return {
        "conversation_id": conv_id,
        "topic": conv_data["topic"],
        "transcript": conv_data.get("transcript", ""),
    }


@router.get("/{conv_id}/messages")
async def get_messages(
    conv_id: str,
    registry: ConversationRegistry = Depends(get_conversation_registry),
):
    """Get conversation messages."""
    conv_data = registry.get(conv_id)
    if not conv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )

    messages = []
    for msg in conv_data.get("messages", []):
        messages.append({
            "agent_id": msg.get("agent_id", 0),
            "agent_name": msg.get("agent_name", "Unknown"),
            "content": msg.get("content", ""),
            "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })

    return {"messages": messages}


@router.post("/{conv_id}/advance")
async def advance_conversation(
    conv_id: str,
    data: Optional[dict] = None,
    circle_registry: CircleRegistry = Depends(get_circle_registry),
    conv_registry: ConversationRegistry = Depends(get_conversation_registry),
):
    """
    Advance a conversation with a new user prompt.

    This continues an existing conversation by adding a user message
    and triggering another round of agent responses.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[ADVANCE] Starting advance for conversation {conv_id}")

    conv_data = conv_registry.get(conv_id)
    if not conv_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conv_id}' not found",
        )

    if conv_data["status"] not in (ConversationStatus.ACTIVE, ConversationStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversation is in {conv_data['status']} status, cannot advance",
        )

    circle = circle_registry.get(conv_data["circle_name"])
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{conv_data['circle_name']}' not found",
        )

    # Add user message to messages list
    user_prompt = data.get("prompt", "") if data else ""

    # Get a fresh copy of messages to avoid mutation issues
    current_messages = list(conv_data.get("messages", []))

    if user_prompt:
        user_timestamp = datetime.now(timezone.utc)
        user_message = {
            "agent_id": 0,
            "agent_name": "User",
            "content": user_prompt,
            "timestamp": user_timestamp,
        }
        current_messages.append(user_message)
        conv_registry.update(conv_id, {"messages": current_messages})

        # Broadcast user message via WebSocket
        await emit_conversation_event(conv_id, "message", {
            "agent_id": 0,
            "agent_name": "User",
            "content": user_prompt,
            "timestamp": user_timestamp.isoformat(),
        })

    # Update status to active if it was completed
    if conv_data["status"] == ConversationStatus.COMPLETED:
        conv_registry.update(conv_id, {"status": ConversationStatus.ACTIVE})

    try:
        # Run another round of collaboration with the new prompt
        result = await circle.collaborate(
            topic=user_prompt or conv_data["topic"],
            agent_ids=conv_data["agent_ids"],
            max_turns=min(5, conv_data["max_turns"]),  # Limit turns for follow-up
            initial_prompt=user_prompt,
        )

        # Get fresh messages after user message was added
        updated_conv = conv_registry.get(conv_id)
        updated_messages = list(updated_conv.get("messages", []))

        logger.info(f"[ADVANCE] Before adding: {len(updated_messages)} messages, {len(result.messages)} new from collaborate")

        # Add agent responses to messages and broadcast each one
        for msg in result.messages:
            msg_data = {
                "agent_id": msg.agent_id,
                "agent_name": msg.agent_name,
                "content": msg.content,
                "mentions": msg.mentions,
                "timestamp": msg.timestamp,
            }
            updated_messages.append(msg_data)

            # Broadcast agent message via WebSocket
            await emit_conversation_event(conv_id, "message", {
                "agent_id": msg.agent_id,
                "agent_name": msg.agent_name,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp),
            })

        logger.info(f"[ADVANCE] After adding: {len(updated_messages)} total messages")

        # Update conversation with new messages
        conv_registry.update(conv_id, {
            "messages": updated_messages,
            "turns_taken": updated_conv.get("turns_taken", 0) + result.turns_taken,
        })

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to advance conversation: {str(e)}",
        )

    return _conv_to_detail(conv_registry.get(conv_id))


# =============================================================================
# Quick Collaboration Endpoint
# =============================================================================


@router.post("/quick", response_model=ConversationDetailResponse)
async def quick_collaborate(
    data: ConversationCreate,
    circle_name: str = "default",
    circle_registry: CircleRegistry = Depends(get_circle_registry),
    conv_registry: ConversationRegistry = Depends(get_conversation_registry),
) -> ConversationDetailResponse:
    """
    Quick collaboration - creates and immediately starts a conversation.

    This is a convenience endpoint that combines create + start.
    """
    circle = circle_registry.get(circle_name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{circle_name}' not found. Create a circle first.",
        )

    if circle.status.value != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Circle must be running to start conversations",
        )

    # Validate agent IDs
    for agent_id in data.agent_ids:
        if agent_id not in circle.agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent {agent_id} not found in circle '{circle_name}'",
            )

    participant_names = [circle.agents[aid].name for aid in data.agent_ids]
    started_at = datetime.now(timezone.utc)

    # Run the collaboration directly
    try:
        result = await circle.collaborate(
            topic=data.topic,
            agent_ids=data.agent_ids,
            max_turns=data.max_turns,
            initial_prompt=data.initial_prompt,
        )

        # Build messages - start with user's initial message if present
        messages = []
        transcript_lines = []
        if data.initial_prompt:
            messages.append({
                "agent_id": 0,
                "agent_name": "User",
                "content": data.initial_prompt,
                "mentions": [],
                "timestamp": started_at,
            })
            transcript_lines.append(f"**User**: {data.initial_prompt}")

        # Add agent messages
        for msg in result.messages:
            messages.append({
                "agent_id": msg.agent_id,
                "agent_name": msg.agent_name,
                "content": msg.content,
                "mentions": msg.mentions,
                "timestamp": msg.timestamp,
            })
            transcript_lines.append(f"**{msg.agent_name}**: {msg.content}")

        transcript = "\n\n".join(transcript_lines)

        conv_data = {
            "topic": data.topic,
            "agent_ids": data.agent_ids,
            "participant_names": participant_names,
            "max_turns": data.max_turns,
            "initial_prompt": data.initial_prompt,
            "turn_strategy": data.turn_strategy,
            "circle_name": circle_name,
            "status": ConversationStatus.COMPLETED,
            "turns_taken": result.turns_taken,
            "messages": messages,
            "transcript": transcript,
            "summary": result.summary,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc),
            "duration_seconds": result.duration_seconds,
        }

        conv_id = conv_registry.add(conv_data)

        # Broadcast all messages for clients that subscribed late
        for msg in messages:
            ts = msg.get("timestamp")
            await emit_conversation_event(conv_id, "message", {
                "agent_id": msg["agent_id"],
                "agent_name": msg["agent_name"],
                "content": msg["content"],
                "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
            })

        return _conv_to_detail(conv_registry.get(conv_id))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collaboration failed: {str(e)}",
        )
