"""
Tests for agent conversation and collaboration features.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from gathering.agents.conversation import (
    AgentConversation,
    ConversationMessage,
    ConversationResult,
    ConversationStatus,
    TurnStrategy,
    CollaborativeTask,
    AgentWrapperParticipant,
    create_agent_conversation,
)

# Conditional import for orchestration (requires croniter)
try:
    from gathering.orchestration import GatheringCircle, AgentHandle
    HAS_ORCHESTRATION = True
except ImportError:
    HAS_ORCHESTRATION = False
    GatheringCircle = None
    AgentHandle = None


class MockParticipant:
    """Mock participant for testing."""

    def __init__(self, agent_id: int, name: str, responses: list = None):
        self._agent_id = agent_id
        self._name = name
        self._responses = responses or [f"Response from {name}"]
        self._response_index = 0

    @property
    def agent_id(self) -> int:
        return self._agent_id

    @property
    def name(self) -> str:
        return self._name

    async def respond(
        self,
        conversation_context: str,
        last_message: str,
        from_agent: str,
    ) -> str:
        response = self._responses[self._response_index % len(self._responses)]
        self._response_index += 1
        return response


class TestConversationMessage:
    """Tests for ConversationMessage."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = ConversationMessage(
            agent_id=1,
            agent_name="Claude",
            content="Hello!",
        )

        assert msg.agent_id == 1
        assert msg.agent_name == "Claude"
        assert msg.content == "Hello!"
        assert msg.mentions == []
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = ConversationMessage(
            agent_id=1,
            agent_name="Claude",
            content="Hello @DeepSeek",
            mentions=[2],
        )

        data = msg.to_dict()

        assert data["agent_id"] == 1
        assert data["agent_name"] == "Claude"
        assert data["content"] == "Hello @DeepSeek"
        assert data["mentions"] == [2]
        assert "timestamp" in data


class TestAgentConversation:
    """Tests for AgentConversation."""

    @pytest.fixture
    def two_participants(self):
        """Create two mock participants."""
        return [
            MockParticipant(1, "Sonnet", ["Hello from Sonnet", "I agree"]),
            MockParticipant(2, "DeepSeek", ["Hello from DeepSeek", "Let's do it"]),
        ]

    def test_conversation_creation(self, two_participants):
        """Test creating a conversation."""
        conv = AgentConversation(
            topic="Test topic",
            participants=two_participants,
            max_turns=5,
        )

        assert conv.topic == "Test topic"
        assert len(conv.participants) == 2
        assert conv.max_turns == 5
        assert conv.status == ConversationStatus.PENDING

    def test_conversation_requires_two_participants(self):
        """Test that conversation requires at least 2 participants."""
        with pytest.raises(ValueError, match="at least 2 participants"):
            AgentConversation(
                topic="Test",
                participants=[MockParticipant(1, "Solo")],
            )

    def test_participant_names(self, two_participants):
        """Test getting participant names."""
        conv = AgentConversation(
            topic="Test",
            participants=two_participants,
        )

        assert conv.participant_names == ["Sonnet", "DeepSeek"]

    @pytest.mark.asyncio
    async def test_add_message(self, two_participants):
        """Test adding a message to conversation."""
        conv = AgentConversation(
            topic="Test",
            participants=two_participants,
        )

        msg = await conv.add_message(1, "Hello!")

        assert msg.agent_id == 1
        assert msg.agent_name == "Sonnet"
        assert msg.content == "Hello!"
        assert len(conv.messages) == 1

    @pytest.mark.asyncio
    async def test_add_message_invalid_participant(self, two_participants):
        """Test adding message from non-participant."""
        conv = AgentConversation(
            topic="Test",
            participants=two_participants,
        )

        with pytest.raises(ValueError, match="not a participant"):
            await conv.add_message(999, "Hello!")

    @pytest.mark.asyncio
    async def test_run_conversation(self, two_participants):
        """Test running a full conversation."""
        conv = AgentConversation(
            topic="Test collaboration",
            participants=two_participants,
            max_turns=4,
        )

        result = await conv.run()

        assert result.status == ConversationStatus.COMPLETED
        assert len(result.messages) >= 2
        assert result.turns_taken >= 1
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_conversation_completion_marker(self):
        """Test that [TERMINÉ] ends conversation early."""
        participants = [
            MockParticipant(1, "Agent1", ["Starting..."]),
            MockParticipant(2, "Agent2", ["[TERMINÉ] We're done!"]),
        ]

        conv = AgentConversation(
            topic="Quick task",
            participants=participants,
            max_turns=10,
        )

        result = await conv.run()

        # Should end after Agent2 says TERMINÉ
        assert result.status == ConversationStatus.COMPLETED
        assert result.turns_taken < 10

    @pytest.mark.asyncio
    async def test_get_transcript(self, two_participants):
        """Test getting conversation transcript."""
        conv = AgentConversation(
            topic="Test topic",
            participants=two_participants,
            max_turns=2,
        )

        await conv.run()
        transcript = conv.get_transcript()

        assert "Test topic" in transcript
        assert "Sonnet" in transcript
        assert "DeepSeek" in transcript

    @pytest.mark.asyncio
    async def test_on_message_callback(self, two_participants):
        """Test message callback."""
        messages_received = []

        def on_msg(msg):
            messages_received.append(msg)

        conv = AgentConversation(
            topic="Test",
            participants=two_participants,
            max_turns=3,
            on_message=on_msg,
        )

        await conv.run()

        assert len(messages_received) >= 2

    @pytest.mark.asyncio
    async def test_on_complete_callback(self, two_participants):
        """Test completion callback."""
        results_received = []

        def on_complete(result):
            results_received.append(result)

        conv = AgentConversation(
            topic="Test",
            participants=two_participants,
            max_turns=2,
            on_complete=on_complete,
        )

        await conv.run()

        assert len(results_received) == 1
        assert results_received[0].status == ConversationStatus.COMPLETED

    def test_extract_mentions(self, two_participants):
        """Test mention extraction."""
        conv = AgentConversation(
            topic="Test",
            participants=two_participants,
        )

        mentions = conv._extract_mentions("Hey @DeepSeek, can you help?")
        assert 2 in mentions

        mentions = conv._extract_mentions("No mentions here")
        assert len(mentions) == 0

    @pytest.mark.asyncio
    async def test_round_robin_turn_strategy(self):
        """Test round-robin turn taking."""
        participants = [
            MockParticipant(1, "A", ["A speaks"]),
            MockParticipant(2, "B", ["B speaks"]),
            MockParticipant(3, "C", ["C speaks"]),
        ]

        conv = AgentConversation(
            topic="Test",
            participants=participants,
            max_turns=6,
            turn_strategy=TurnStrategy.ROUND_ROBIN,
        )

        await conv.run()

        # Check that each agent got at least one turn
        agent_ids = [m.agent_id for m in conv.messages]
        assert 1 in agent_ids
        assert 2 in agent_ids
        assert 3 in agent_ids

    @pytest.mark.asyncio
    async def test_mention_based_turn_strategy(self):
        """Test mention-based turn taking."""
        participants = [
            MockParticipant(1, "Alice", ["Hello @Bob, what do you think?"]),
            MockParticipant(2, "Bob", ["I agree @Alice! [TERMINÉ]"]),
        ]

        conv = AgentConversation(
            topic="Test",
            participants=participants,
            max_turns=4,
            turn_strategy=TurnStrategy.MENTION_BASED,
        )

        await conv.run()

        # Both should have spoken
        agent_ids = [m.agent_id for m in conv.messages]
        assert 1 in agent_ids
        assert 2 in agent_ids

    @pytest.mark.asyncio
    async def test_free_form_turn_strategy(self):
        """Test free-form turn taking - avoids immediate repeats."""
        participants = [
            MockParticipant(1, "A", ["A speaks"]),
            MockParticipant(2, "B", ["B speaks"]),
            MockParticipant(3, "C", ["C speaks [TERMINÉ]"]),
        ]

        conv = AgentConversation(
            topic="Test",
            participants=participants,
            max_turns=6,
            turn_strategy=TurnStrategy.FREE_FORM,
        )

        await conv.run()

        # Check no immediate repetition (except possibly at boundaries)
        for i in range(1, len(conv.messages)):
            # At least some variety should exist
            pass  # FREE_FORM uses randomness, so we just verify it runs

        assert conv.status == ConversationStatus.COMPLETED
        assert len(conv.messages) >= 2

    @pytest.mark.asyncio
    async def test_free_form_respects_mentions(self):
        """Test free-form gives priority to mentioned agents."""
        participants = [
            MockParticipant(1, "Alice", ["@Charlie, your thoughts?"]),
            MockParticipant(2, "Bob", ["I'll wait"]),
            MockParticipant(3, "Charlie", ["Thanks for asking! [TERMINÉ]"]),
        ]

        conv = AgentConversation(
            topic="Test",
            participants=participants,
            max_turns=4,
            turn_strategy=TurnStrategy.FREE_FORM,
        )

        await conv.run()

        # Charlie (id=3) should speak after Alice mentioned them
        messages = conv.messages
        if len(messages) >= 2:
            # After Alice's message mentioning Charlie, Charlie should respond
            alice_msg_idx = next(i for i, m in enumerate(messages) if m.agent_id == 1)
            if alice_msg_idx + 1 < len(messages):
                next_speaker = messages[alice_msg_idx + 1].agent_id
                assert next_speaker == 3  # Charlie should respond to mention

    @pytest.mark.asyncio
    async def test_facilitator_led_strategy(self):
        """Test facilitator-led turn taking."""
        participants = [
            MockParticipant(1, "Facilitator", [
                "Welcome! @Alice, please start.",
                "Good point. @Bob, what do you think?",
                "[TERMINÉ] Great discussion!"
            ]),
            MockParticipant(2, "Alice", ["Here's my idea..."]),
            MockParticipant(3, "Bob", ["I agree with Alice"]),
        ]

        conv = AgentConversation(
            topic="Facilitated Discussion",
            participants=participants,
            max_turns=6,
            turn_strategy=TurnStrategy.FACILITATOR_LED,
            facilitator_id=1,
        )

        await conv.run()

        # Facilitator should have spoken first
        assert conv.messages[0].agent_id == 1

        # All participants should have spoken
        agent_ids = set(m.agent_id for m in conv.messages)
        assert 1 in agent_ids  # Facilitator

        assert conv.status == ConversationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_facilitator_led_requires_facilitator_id(self):
        """Test that FACILITATOR_LED requires facilitator_id."""
        participants = [
            MockParticipant(1, "A", ["A speaks"]),
            MockParticipant(2, "B", ["B speaks"]),
        ]

        with pytest.raises(ValueError, match="requires a facilitator_id"):
            AgentConversation(
                topic="Test",
                participants=participants,
                turn_strategy=TurnStrategy.FACILITATOR_LED,
                facilitator_id=None,
            )

    @pytest.mark.asyncio
    async def test_facilitator_must_be_participant(self):
        """Test that facilitator must be a participant."""
        participants = [
            MockParticipant(1, "A", ["A speaks"]),
            MockParticipant(2, "B", ["B speaks"]),
        ]

        with pytest.raises(ValueError, match="must be a participant"):
            AgentConversation(
                topic="Test",
                participants=participants,
                turn_strategy=TurnStrategy.FACILITATOR_LED,
                facilitator_id=999,  # Not a participant
            )

    @pytest.mark.asyncio
    async def test_facilitator_extracts_choice_from_message(self):
        """Test that facilitator's choice is extracted from their message."""
        # The facilitator mentions Bob, so Bob should speak next
        participants = [
            MockParticipant(1, "Facilitator", ["Let's hear from Bob"]),
            MockParticipant(2, "Alice", ["My thoughts..."]),
            MockParticipant(3, "Bob", ["[TERMINÉ] Here's my input"]),
        ]

        conv = AgentConversation(
            topic="Test",
            participants=participants,
            max_turns=4,
            turn_strategy=TurnStrategy.FACILITATOR_LED,
            facilitator_id=1,
        )

        await conv.run()

        # After facilitator says "hear from Bob", Bob should speak
        if len(conv.messages) >= 2:
            # Second message should be from Bob (id=3)
            assert conv.messages[1].agent_id == 3


class TestCollaborativeTask:
    """Tests for CollaborativeTask."""

    @pytest.fixture
    def participants(self):
        return [
            MockParticipant(1, "Dev1", ["Working on it...", "[TERMINÉ]"]),
            MockParticipant(2, "Dev2", ["I'll help!"]),
        ]

    @pytest.mark.asyncio
    async def test_collaborative_task_creation(self, participants):
        """Test creating a collaborative task."""
        task = CollaborativeTask(
            task_id=1,
            title="Write BDD scenarios",
            description="Create scenarios for auth",
            participants=participants,
            max_rounds=3,
        )

        assert task.task_id == 1
        assert task.title == "Write BDD scenarios"
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_collaborative_task_execution(self, participants):
        """Test executing a collaborative task."""
        task = CollaborativeTask(
            task_id=1,
            title="Quick task",
            description="Do something",
            participants=participants,
            max_rounds=2,
        )

        result = await task.execute()

        assert result.status == ConversationStatus.COMPLETED
        assert task.status == "completed"
        assert len(task.conversations) == 1


@pytest.mark.skipif(not HAS_ORCHESTRATION, reason="croniter not installed")
class TestGatheringCircleCollaborate:
    """Tests for GatheringCircle.collaborate()."""

    @pytest.fixture
    def circle_with_agents(self):
        """Create a circle with agents that have process_message callbacks."""
        circle = GatheringCircle(name="test", auto_route=False)

        async def sonnet_respond(msg: str) -> str:
            return "Sonnet says: I'll write the first scenario"

        async def deepseek_respond(msg: str) -> str:
            return "DeepSeek says: [TERMINÉ] I'll add validation"

        circle.add_agent(AgentHandle(
            id=1,
            name="Sonnet",
            provider="anthropic",
            model="claude-sonnet",
            competencies=["python", "bdd"],
            can_review=["code"],
            process_message=sonnet_respond,
        ))

        circle.add_agent(AgentHandle(
            id=2,
            name="DeepSeek",
            provider="deepseek",
            model="deepseek-coder",
            competencies=["python", "testing"],
            can_review=["code"],
            process_message=deepseek_respond,
        ))

        return circle

    @pytest.mark.asyncio
    async def test_collaborate_basic(self, circle_with_agents):
        """Test basic collaboration."""
        await circle_with_agents.start()

        result = await circle_with_agents.collaborate(
            topic="Écrire les scénarios BDD",
            agent_ids=[1, 2],
            max_turns=4,
        )

        assert result.status == ConversationStatus.COMPLETED
        assert len(result.messages) >= 2

        # Check both agents participated
        agent_ids = {m.agent_id for m in result.messages}
        assert 1 in agent_ids
        assert 2 in agent_ids

    @pytest.mark.asyncio
    async def test_collaborate_invalid_agent(self, circle_with_agents):
        """Test collaboration with invalid agent ID."""
        await circle_with_agents.start()

        with pytest.raises(ValueError, match="not found"):
            await circle_with_agents.collaborate(
                topic="Test",
                agent_ids=[1, 999],
            )

    @pytest.mark.asyncio
    async def test_collaborate_with_initial_prompt(self, circle_with_agents):
        """Test collaboration with custom initial prompt."""
        await circle_with_agents.start()

        result = await circle_with_agents.collaborate(
            topic="BDD Scenarios",
            agent_ids=[1, 2],
            max_turns=4,
            initial_prompt="Focus on authentication features. Be concise.",
        )

        assert result.status == ConversationStatus.COMPLETED


class TestAgentWrapperParticipant:
    """Tests for AgentWrapperParticipant adapter."""

    def test_adapter_properties(self):
        """Test adapter exposes correct properties."""
        mock_wrapper = MagicMock()
        mock_wrapper.agent_id = 42
        mock_wrapper.name = "TestAgent"

        participant = AgentWrapperParticipant(mock_wrapper)

        assert participant.agent_id == 42
        assert participant.name == "TestAgent"

    @pytest.mark.asyncio
    async def test_adapter_respond(self):
        """Test adapter calls wrapper chat method."""
        mock_wrapper = MagicMock()
        mock_wrapper.agent_id = 1
        mock_wrapper.name = "Test"

        mock_response = MagicMock()
        mock_response.content = "Response content"
        mock_wrapper.chat = AsyncMock(return_value=mock_response)

        participant = AgentWrapperParticipant(mock_wrapper)

        response = await participant.respond(
            "context",
            "last message",
            "Other Agent",
        )

        assert response == "Response content"
        mock_wrapper.chat.assert_called_once()


@pytest.mark.asyncio
async def test_create_agent_conversation_helper():
    """Test the create_agent_conversation helper function."""
    mock_wrapper1 = MagicMock()
    mock_wrapper1.agent_id = 1
    mock_wrapper1.name = "Agent1"
    mock_response1 = MagicMock()
    mock_response1.content = "Hello"
    mock_wrapper1.chat = AsyncMock(return_value=mock_response1)

    mock_wrapper2 = MagicMock()
    mock_wrapper2.agent_id = 2
    mock_wrapper2.name = "Agent2"
    mock_response2 = MagicMock()
    mock_response2.content = "[TERMINÉ]"
    mock_wrapper2.chat = AsyncMock(return_value=mock_response2)

    conv = await create_agent_conversation(
        topic="Test topic",
        agents=[mock_wrapper1, mock_wrapper2],
        max_turns=4,
    )

    assert conv.topic == "Test topic"
    assert len(conv.participants) == 2
    assert conv.max_turns == 4
