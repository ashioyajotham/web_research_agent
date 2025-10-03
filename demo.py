"""
Demo script to showcase the Web Research Agent capabilities.
Runs a simple task and shows the reasoning process.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from llm import LLMInterface
from tools import ToolManager, SearchTool, ScrapeTool, CodeExecutorTool, FileOpsTool
from agent import ReActAgent


def print_banner():
    """Print a nice banner."""
    print("\n" + "=" * 80)
    print(" " * 20 + "WEB RESEARCH AGENT DEMO")
    print("=" * 80 + "\n")


def print_step(step_num, thought, action=None, action_input=None):
    """Print a step in a formatted way."""
    print(f"\n{'─' * 80}")
    print(f"STEP {step_num}")
    print(f"{'─' * 80}")
    print(f"\n💭 Thought: {thought}")

    if action:
        print(f"\n🔧 Action: {action}")
        if action_input:
            print(f"   Input: {action_input}")


def main():
    """Run a demo task."""
    print_banner()

    # Check configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease set up your .env file with API keys.")
        print("See QUICKSTART.md for instructions.")
        return 1

    print("✓ Configuration validated")
    print(f"  Model: {config.model_name}")
    print(f"  Max iterations: {config.max_iterations}")

    # Initialize components
    print("\n📦 Initializing agent...")

    llm = LLMInterface(
        api_key=config.gemini_api_key,
        model_name=config.model_name,
        temperature=config.temperature,
    )

    tool_manager = ToolManager()
    tool_manager.register_tool(SearchTool(config.serper_api_key))
    tool_manager.register_tool(ScrapeTool())
    tool_manager.register_tool(CodeExecutorTool())
    tool_manager.register_tool(FileOpsTool())

    print(f"  Registered {len(tool_manager.get_all_tools())} tools")

    agent = ReActAgent(
        llm=llm,
        tool_manager=tool_manager,
        max_iterations=config.max_iterations,
    )

    # Demo task
    demo_task = "What is the current CEO of Microsoft and when did they become CEO?"

    print("\n" + "=" * 80)
    print("DEMO TASK")
    print("=" * 80)
    print(f"\n{demo_task}\n")

    print("🤔 Agent is thinking...\n")

    # Run the agent
    start_time = datetime.now()

    try:
        answer = agent.run(demo_task)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Show the reasoning process
        print("\n" + "=" * 80)
        print("REASONING PROCESS")
        print("=" * 80)

        trace = agent.get_execution_trace()
        for i, step in enumerate(trace, 1):
            print_step(i, step["thought"], step.get("action"), step.get("action_input"))

            if "observation" in step:
                obs = step["observation"]
                if len(obs) > 200:
                    obs = obs[:200] + "..."
                print(f"\n📊 Observation: {obs}")

        # Show final answer
        print("\n" + "=" * 80)
        print("FINAL ANSWER")
        print("=" * 80)
        print(f"\n{answer}\n")

        print("=" * 80)
        print(f"✓ Completed in {execution_time:.2f} seconds ({len(trace)} steps)")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
