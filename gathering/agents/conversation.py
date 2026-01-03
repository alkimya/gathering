"""
Agent Conversation - Enables direct communication between agents.
Allows multiple agents to collaborate on tasks through structured conversations.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol

if TYPE_CHECKING:
    from gathering.agents.wrapper import AgentWrapper
from datetime import datetime, timezone
from enum import Enum
import asyncio


class ConversationStatus(Enum):
    """Status of a conversation."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnStrategy(Enum):
    """Strategy for managing turns in conversation."""
    ROUND_ROBIN = "round_robin"  # Each agent speaks in order
    MENTION_BASED = "mention_based"  # Agent speaks when mentioned
    FREE_FORM = "free_form"  # Any agent can speak anytime
    FACILITATOR_LED = "facilitator_led"  # Facilitator decides who speaks


@dataclass
class ConversationMessage:
    """A message in an agent conversation."""
    agent_id: int
    agent_name: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mentions: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "mentions": self.mentions,
            "metadata": self.metadata,
        }


@dataclass
class ConversationResult:
    """Result of a completed conversation."""
    status: ConversationStatus
    messages: List[ConversationMessage]
    summary: str = ""
    artifacts: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    turns_taken: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentParticipant(Protocol):
    """Protocol for agents participating in conversations."""

    @property
    def agent_id(self) -> int:
        """Agent's unique identifier."""
        ...

    @property
    def name(self) -> str:
        """Agent's name."""
        ...

    async def respond(
        self,
        conversation_context: str,
        last_message: str,
        from_agent: str,
    ) -> str:
        """Generate a response in the conversation."""
        ...


@dataclass
class AgentConversation:
    """
    A conversation between multiple agents.

    Enables structured collaboration where agents can discuss,
    debate, and work together on a topic or task.

    Usage:
        conversation = AgentConversation(
            topic="Écrire les scénarios BDD pour l'authentification",
            participants=[sonnet, deepseek],
            max_turns=10,
        )

        result = await conversation.run()
        print(result.summary)
    """

    topic: str
    participants: List[AgentParticipant]
    max_turns: int = 10
    turn_strategy: TurnStrategy = TurnStrategy.ROUND_ROBIN
    initial_prompt: str = ""
    facilitator_id: Optional[int] = None  # Required for FACILITATOR_LED strategy

    # State
    status: ConversationStatus = ConversationStatus.PENDING
    messages: List[ConversationMessage] = field(default_factory=list)
    current_turn: int = 0
    current_speaker_index: int = 0
    _last_facilitator_choice: Optional[int] = field(default=None, repr=False)

    # Callbacks
    on_message: Optional[Callable[[ConversationMessage], None]] = None
    on_turn_complete: Optional[Callable[[int], None]] = None
    on_complete: Optional[Callable[[ConversationResult], None]] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Configuration
    timeout_per_turn: int = 60  # seconds
    summary_prompt: str = ""

    def __post_init__(self):
        if len(self.participants) < 2:
            raise ValueError("A conversation requires at least 2 participants")

        # Validate facilitator for FACILITATOR_LED strategy
        if self.turn_strategy == TurnStrategy.FACILITATOR_LED:
            if self.facilitator_id is None:
                raise ValueError("FACILITATOR_LED strategy requires a facilitator_id")
            participant_ids = [p.agent_id for p in self.participants]
            if self.facilitator_id not in participant_ids:
                raise ValueError(f"Facilitator {self.facilitator_id} must be a participant")

        # Build participant map
        self._participant_map: Dict[int, AgentParticipant] = {
            p.agent_id: p for p in self.participants
        }

    @property
    def participant_names(self) -> List[str]:
        """Names of all participants."""
        return [p.name for p in self.participants]

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    def _build_context(self, for_agent_id: Optional[int] = None) -> str:
        """Build conversation context for agents."""
        lines = [
            f"## Conversation: {self.topic}",
            f"Participants: {', '.join(self.participant_names)}",
            "",
        ]

        # Add facilitator instructions if applicable
        if self.turn_strategy == TurnStrategy.FACILITATOR_LED and for_agent_id == self.facilitator_id:
            other_participants = [p.name for p in self.participants if p.agent_id != self.facilitator_id]
            lines.append("**Tu es le facilitateur de cette conversation.**")
            lines.append("Ton rôle est de guider la discussion et de décider qui parle.")
            lines.append(f"Pour donner la parole à quelqu'un, mentionne son nom: {', '.join(other_participants)}")
            lines.append("")

        if self.initial_prompt:
            lines.append(f"Instructions: {self.initial_prompt}")
            lines.append("")

        if self.messages:
            lines.append("### Historique de la conversation:")
            for msg in self.messages[-10:]:  # Last 10 messages
                lines.append(f"**{msg.agent_name}**: {msg.content}")
            lines.append("")

        return "\n".join(lines)

    def _get_next_speaker(self) -> AgentParticipant:
        """Determine the next speaker based on strategy."""
        if self.turn_strategy == TurnStrategy.ROUND_ROBIN:
            speaker = self.participants[self.current_speaker_index]
            self.current_speaker_index = (
                self.current_speaker_index + 1
            ) % len(self.participants)
            return speaker

        elif self.turn_strategy == TurnStrategy.MENTION_BASED:
            # Check last message for mentions
            if self.messages:
                last_msg = self.messages[-1]
                if last_msg.mentions:
                    mentioned_id = last_msg.mentions[0]
                    if mentioned_id in self._participant_map:
                        return self._participant_map[mentioned_id]

            # Fallback to round robin
            speaker = self.participants[self.current_speaker_index]
            self.current_speaker_index = (
                self.current_speaker_index + 1
            ) % len(self.participants)
            return speaker

        elif self.turn_strategy == TurnStrategy.FREE_FORM:
            # Any agent can speak - choose based on who hasn't spoken recently
            # or who was mentioned, with some randomness
            if self.messages:
                last_msg = self.messages[-1]
                # If someone was mentioned, they speak
                if last_msg.mentions:
                    mentioned_id = last_msg.mentions[0]
                    if mentioned_id in self._participant_map:
                        return self._participant_map[mentioned_id]

                # Otherwise, pick someone who didn't just speak
                # Count recent messages (last 3) by speaker
                recent_speakers = [m.agent_id for m in self.messages[-3:]]

                # Find agents who haven't spoken recently
                candidates = [
                    p for p in self.participants
                    if p.agent_id not in recent_speakers[-1:]  # Just avoid immediate repeat
                ]

                if candidates:
                    # Rotate through candidates
                    import random
                    return random.choice(candidates)

            # Fallback to round robin for first message
            speaker = self.participants[self.current_speaker_index]
            self.current_speaker_index = (
                self.current_speaker_index + 1
            ) % len(self.participants)
            return speaker

        elif self.turn_strategy == TurnStrategy.FACILITATOR_LED:
            # Facilitator decides who speaks next
            # If we have a pending choice from facilitator, use it
            if self._last_facilitator_choice is not None:
                chosen_id = self._last_facilitator_choice
                self._last_facilitator_choice = None
                if chosen_id in self._participant_map:
                    return self._participant_map[chosen_id]

            # Otherwise, facilitator speaks to direct the conversation
            return self._participant_map[self.facilitator_id]

        else:
            # Default: round robin
            speaker = self.participants[self.current_speaker_index]
            self.current_speaker_index = (
                self.current_speaker_index + 1
            ) % len(self.participants)
            return speaker

    def _extract_facilitator_choice(self, content: str) -> Optional[int]:
        """Extract who the facilitator wants to speak next from their message."""
        # Look for patterns like "@AgentName, your turn" or "I'd like to hear from @AgentName"
        for participant in self.participants:
            if participant.agent_id == self.facilitator_id:
                continue  # Skip facilitator themselves

            # Check for @mention
            if f"@{participant.name}" in content:
                return participant.agent_id

            # Check for "AgentName, ..." at start of sentence or after common phrases
            patterns = [
                f"{participant.name}, ",
                f"{participant.name}?",
                f"ask {participant.name}",
                f"hear from {participant.name}",
                f"{participant.name} should",
                f"{participant.name} can",
            ]
            content_lower = content.lower()
            name_lower = participant.name.lower()
            for pattern in patterns:
                if pattern.lower().replace(participant.name.lower(), name_lower) in content_lower:
                    return participant.agent_id

        return None

    def _extract_mentions(self, content: str) -> List[int]:
        """Extract @mentions from message content."""
        mentions = []
        for participant in self.participants:
            if f"@{participant.name}" in content:
                mentions.append(participant.agent_id)
        return mentions

    def _check_completion(self, content: str) -> bool:
        """Check if conversation should end."""
        completion_markers = [
            "[TERMINÉ]",
            "[DONE]",
            "[FIN]",
            "[COMPLETE]",
            "nous avons terminé",
            "c'est tout pour",
            "voilà les scénarios",
        ]
        content_lower = content.lower()
        return any(marker.lower() in content_lower for marker in completion_markers)

    async def _generate_summary(self) -> str:
        """Generate a summary of the conversation."""
        if not self.messages:
            return "Aucun message dans la conversation."

        # Simple summary: list key points from each participant
        lines = [f"## Résumé: {self.topic}", ""]

        # Group messages by participant
        by_participant: Dict[str, List[str]] = {}
        for msg in self.messages:
            if msg.agent_name not in by_participant:
                by_participant[msg.agent_name] = []
            # Take first 100 chars of each message
            by_participant[msg.agent_name].append(msg.content[:100])

        for name, contents in by_participant.items():
            lines.append(f"### Contributions de {name}:")
            for i, content in enumerate(contents[:5], 1):
                lines.append(f"{i}. {content}...")
            lines.append("")

        lines.append(f"Total: {len(self.messages)} messages, {self.current_turn} tours")

        return "\n".join(lines)

    async def add_message(
        self,
        agent_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """Add a message to the conversation."""
        participant = self._participant_map.get(agent_id)
        if not participant:
            raise ValueError(f"Agent {agent_id} is not a participant")

        message = ConversationMessage(
            agent_id=agent_id,
            agent_name=participant.name,
            content=content,
            mentions=self._extract_mentions(content),
            metadata=metadata or {},
        )

        self.messages.append(message)

        # For FACILITATOR_LED: extract who the facilitator wants to speak next
        if (self.turn_strategy == TurnStrategy.FACILITATOR_LED
                and agent_id == self.facilitator_id):
            choice = self._extract_facilitator_choice(content)
            if choice is not None:
                self._last_facilitator_choice = choice

        if self.on_message:
            self.on_message(message)

        return message

    async def run(self) -> ConversationResult:
        """
        Run the conversation until completion or max turns.

        Returns:
            ConversationResult with all messages and summary
        """
        self.status = ConversationStatus.ACTIVE
        self.started_at = datetime.now(timezone.utc)

        try:
            # Initial message to kick off the conversation
            # For FACILITATOR_LED, facilitator starts; otherwise first participant
            if self.turn_strategy == TurnStrategy.FACILITATOR_LED:
                first_speaker = self._participant_map[self.facilitator_id]
            else:
                first_speaker = self.participants[0]

            context = self._build_context(for_agent_id=first_speaker.agent_id)

            initial_prompt = self.initial_prompt or f"Commençons à discuter de: {self.topic}"

            first_response = await asyncio.wait_for(
                first_speaker.respond(
                    conversation_context=context,
                    last_message=initial_prompt,
                    from_agent="System",
                ),
                timeout=self.timeout_per_turn,
            )

            await self.add_message(first_speaker.agent_id, first_response)
            self.current_turn = 1

            if self.on_turn_complete:
                self.on_turn_complete(self.current_turn)

            # Main conversation loop
            while self.current_turn < self.max_turns:
                # Get next speaker
                speaker = self._get_next_speaker()

                # Skip if same as last speaker (for round robin with 2 agents)
                if self.messages and self.messages[-1].agent_id == speaker.agent_id:
                    speaker = self._get_next_speaker()

                # Build context (with facilitator instructions if applicable)
                context = self._build_context(for_agent_id=speaker.agent_id)
                last_msg = self.messages[-1]

                # Get response
                try:
                    response = await asyncio.wait_for(
                        speaker.respond(
                            conversation_context=context,
                            last_message=last_msg.content,
                            from_agent=last_msg.agent_name,
                        ),
                        timeout=self.timeout_per_turn,
                    )
                except asyncio.TimeoutError:
                    response = f"[Timeout - {speaker.name} n'a pas répondu à temps]"

                await self.add_message(speaker.agent_id, response)
                self.current_turn += 1

                if self.on_turn_complete:
                    self.on_turn_complete(self.current_turn)

                # Check if conversation should end
                if self._check_completion(response):
                    break

            self.status = ConversationStatus.COMPLETED

        except Exception as e:
            self.status = ConversationStatus.FAILED
            await self.add_message(
                self.participants[0].agent_id,
                f"[Erreur: {str(e)}]",
                metadata={"error": True},
            )

        finally:
            self.completed_at = datetime.now(timezone.utc)

        # Generate result
        summary = await self._generate_summary()

        result = ConversationResult(
            status=self.status,
            messages=self.messages,
            summary=summary,
            duration_seconds=self.duration,
            turns_taken=self.current_turn,
        )

        if self.on_complete:
            self.on_complete(result)

        return result

    async def pause(self) -> None:
        """Pause the conversation."""
        self.status = ConversationStatus.PAUSED

    async def resume(self) -> ConversationResult:
        """Resume a paused conversation."""
        if self.status != ConversationStatus.PAUSED:
            raise ValueError("Can only resume paused conversations")
        return await self.run()

    def get_transcript(self) -> str:
        """Get full transcript of the conversation."""
        lines = [
            f"# Transcript: {self.topic}",
            f"Participants: {', '.join(self.participant_names)}",
            f"Date: {self.started_at.isoformat() if self.started_at else 'N/A'}",
            f"Status: {self.status.value}",
            "",
            "---",
            "",
        ]

        for msg in self.messages:
            lines.append(f"**{msg.agent_name}** ({msg.timestamp.strftime('%H:%M:%S')}):")
            lines.append(msg.content)
            lines.append("")

        return "\n".join(lines)


class CollaborativeTask:
    """
    A task that multiple agents work on together.

    Unlike a regular task assigned to one agent, a collaborative task
    involves multiple agents contributing through conversation.
    """

    def __init__(
        self,
        task_id: int,
        title: str,
        description: str,
        participants: List[AgentParticipant],
        max_rounds: int = 5,
    ):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.participants = participants
        self.max_rounds = max_rounds

        self.conversations: List[AgentConversation] = []
        self.artifacts: List[str] = []
        self.status: str = "pending"

    async def execute(self) -> ConversationResult:
        """
        Execute the collaborative task.

        Returns:
            ConversationResult with the outcome
        """
        self.status = "in_progress"

        # Create main conversation
        conversation = AgentConversation(
            topic=self.title,
            participants=self.participants,
            max_turns=self.max_rounds * len(self.participants),
            initial_prompt=f"""
Tâche collaborative: {self.title}

{self.description}

Travaillez ensemble pour accomplir cette tâche. Chacun peut contribuer
selon ses compétences. Terminez par [TERMINÉ] quand vous avez fini.
""",
        )

        self.conversations.append(conversation)
        result = await conversation.run()

        if result.status == ConversationStatus.COMPLETED:
            self.status = "completed"
        else:
            self.status = "failed"

        return result


# Adapter to make AgentWrapper compatible with AgentParticipant
class AgentWrapperParticipant:
    """Adapter to use AgentWrapper in conversations."""

    def __init__(self, wrapper: "AgentWrapper"):
        self._wrapper = wrapper

    @property
    def agent_id(self) -> int:
        return self._wrapper.agent_id

    @property
    def name(self) -> str:
        return self._wrapper.name

    async def respond(
        self,
        conversation_context: str,
        last_message: str,
        from_agent: str,
    ) -> str:
        """Generate response using the wrapped agent."""
        prompt = f"""
{conversation_context}

{from_agent} vient de dire: "{last_message}"

Réponds de manière concise et constructive. Si tu as terminé ta contribution,
inclus [TERMINÉ] dans ta réponse.
"""
        response = await self._wrapper.chat(prompt, include_memories=True)
        return response.content


# Convenience function
async def create_agent_conversation(
    topic: str,
    agents: List["AgentWrapper"],
    max_turns: int = 10,
    initial_prompt: str = "",
) -> AgentConversation:
    """
    Create a conversation between AgentWrapper instances.

    Args:
        topic: What the conversation is about
        agents: List of AgentWrapper instances
        max_turns: Maximum number of turns
        initial_prompt: Optional initial instructions

    Returns:
        AgentConversation ready to run
    """
    participants = [AgentWrapperParticipant(agent) for agent in agents]

    return AgentConversation(
        topic=topic,
        participants=participants,
        max_turns=max_turns,
        initial_prompt=initial_prompt,
    )
