#!/usr/bin/env python3
"""
GatheRing Framework Quick Start Script
Run this to verify your installation and see basic functionality.
"""

import sys
from pathlib import Path

# Add gathering to path for development
sys.path.insert(0, str(Path(__file__).parent))

from gathering.core.implementations import BasicAgent, BasicConversation, BasicPersonalityBlock, CalculatorTool


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f"  {text}")
    print("=" * 50 + "\n")


def demo_basic_agent():
    """Demonstrate basic agent creation and interaction."""
    print_header("Basic Agent Demo")

    # Create a simple agent
    agent = BasicAgent.from_config({"name": "Assistant", "llm_provider": "openai", "model": "gpt-4"})

    print(f"Created agent: {agent.name}")
    print(f"Agent ID: {agent.id}")

    # Process a message
    response = agent.process_message("Hello! What's your name?")
    print("\nUser: Hello! What's your name?")
    print(f"Agent: {response}")

    # Test memory
    agent.process_message("My name is Alice")
    response2 = agent.process_message("What's my name?")
    print("\nUser: My name is Alice")
    print("User: What's my name?")
    print(f"Agent: {response2}")


def demo_personality():
    """Demonstrate agent with personality."""
    print_header("Personality Demo")

    # Create agent with personality
    agent = BasicAgent.from_config(
        {
            "name": "Dr. Curious",
            "age": 42,
            "history": "A researcher with 20 years of experience",
            "llm_provider": "anthropic",
            "model": "claude-3",
        }
    )

    # Add personality blocks
    curious = BasicPersonalityBlock.from_config({"type": "trait", "name": "curious", "intensity": 0.9})

    analytical = BasicPersonalityBlock.from_config({"type": "behavior", "name": "analytical", "intensity": 0.7})

    agent.add_personality_block(curious)
    agent.add_personality_block(analytical)

    print(f"Agent: {agent.name}")
    print(f"Age: {agent.age}")
    print(f"History: {agent.history}")
    print(f"Personality traits: {[b.name for b in agent.personality_blocks]}")
    print(f"\nSystem prompt:\n{agent.get_system_prompt()}")


def demo_tools():
    """Demonstrate agent using tools."""
    print_header("Tools Demo")

    # Create agent with calculator tool
    agent = BasicAgent.from_config({"name": "MathBot", "llm_provider": "openai", "model": "gpt-4"})

    # Add calculator tool
    calculator = CalculatorTool.from_config({"name": "calculator", "type": "calculator"})
    agent.add_tool(calculator)

    print(f"Agent: {agent.name}")
    print(f"Available tools: {list(agent.tools.keys())}")

    # Test calculation
    calc_result = calculator.execute("15% of 2500")
    print(f"\nDirect tool test: 15% of 2500 = {calc_result.output}")


def demo_conversation():
    """Demonstrate multi-agent conversation."""
    print_header("Multi-Agent Conversation Demo")

    # Create two agents
    teacher = BasicAgent.from_config(
        {"name": "Professor Smith", "age": 50, "llm_provider": "openai", "model": "gpt-4"}
    )

    student = BasicAgent.from_config({"name": "Alice", "age": 20, "llm_provider": "anthropic", "model": "claude-3"})

    # Add personalities
    teacher.add_personality_block(
        BasicPersonalityBlock.from_config({"type": "trait", "name": "patient", "intensity": 0.8})
    )

    student.add_personality_block(
        BasicPersonalityBlock.from_config({"type": "trait", "name": "curious", "intensity": 0.9})
    )

    print(f"Participants: {teacher.name} and {student.name}")

    # Create conversation
    conversation = BasicConversation.create([teacher, student])

    # Simulate conversation
    conversation.add_message(student, "Can you explain what recursion is?")
    print(f"\n{student.name}: Can you explain what recursion is?")

    responses = conversation.process_turn()
    for resp in responses:
        print(f"{resp['agent'].name}: {resp['content']}")


def run_tests():
    """Run basic tests to verify installation."""
    print_header("Running Basic Tests")

    try:
        # Test 1: Agent creation
        agent = BasicAgent.from_config({"name": "Test", "llm_provider": "openai", "model": "gpt-4"})
        print("✓ Agent creation successful")

        # Test 2: Memory functionality
        agent.process_message("Test message")
        history = agent.memory.get_conversation_history()
        assert len(history) > 0
        print("✓ Memory functionality working")

        # Test 3: Tool creation
        tool = CalculatorTool.from_config({"name": "calc"})
        result = tool.execute("2 + 2")
        assert result.output == 4
        print("✓ Tool functionality working")

        # Test 4: Personality blocks
        block = BasicPersonalityBlock.from_config({"type": "trait", "name": "friendly", "intensity": 0.5})
        assert block.get_prompt_modifiers() != ""
        print("✓ Personality system working")

        print("\n✅ All basic tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        return False

    return True


def main():
    """Run all demos."""
    print("\n🤝 Welcome to GatheRing - Collaborative Multi-Agent AI Framework")
    print("This quick start will demonstrate the basic functionality.\n")

    # Run tests first
    if not run_tests():
        print("\n⚠️  Some tests failed. Please check your installation.")
        return

    # Run demos
    try:
        demo_basic_agent()
        demo_personality()
        demo_tools()
        demo_conversation()

        print_header("Quick Start Complete!")
        print("✨ GatheRing is ready to use!")
        print("\nNext steps:")
        print("1. Run full test suite: pytest")
        print("2. Check coverage: pytest --cov=gathering")
        print("3. Read the documentation: docs/")
        print("4. Start building your own agents!")

    except Exception as e:
        print(f"\n❌ Error during demo: {str(e)}")
        print("Please check your installation and dependencies.")


if __name__ == "__main__":
    main()
