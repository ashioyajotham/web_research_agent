"""
Main entry point for the Web Research Agent.
Processes tasks from a file and runs the ReAct agent on each task.
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from typing import List

from config import config
from llm import LLMInterface
from tools import ToolManager, SearchTool, ScrapeTool, CodeExecutorTool, FileOpsTool
from agent import ReActAgent


# Configure logging
def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/agent_{timestamp}.log"

    # Configure logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")


def read_tasks(task_file: str) -> List[str]:
    """
    Read tasks from a file.

    Args:
        task_file: Path to the task file (one task per line)

    Returns:
        List of task strings
    """
    logger = logging.getLogger(__name__)

    try:
        with open(task_file, "r", encoding="utf-8") as f:
            tasks = []
            current_task = []

            for line in f:
                line = line.rstrip()

                # Empty line separates tasks
                if not line:
                    if current_task:
                        tasks.append("\n".join(current_task))
                        current_task = []
                else:
                    current_task.append(line)

            # Add the last task if there is one
            if current_task:
                tasks.append("\n".join(current_task))

        logger.info(f"Read {len(tasks)} tasks from {task_file}")
        return tasks

    except FileNotFoundError:
        logger.error(f"Task file not found: {task_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading task file: {str(e)}")
        sys.exit(1)


def initialize_agent(verbose: bool = False) -> ReActAgent:
    """
    Initialize the ReAct agent with LLM and tools.

    Args:
        verbose: If True, show detailed logging output

    Returns:
        Configured ReActAgent instance
    """
    logger = logging.getLogger(__name__)

    # Suppress info logs if not verbose
    if not verbose:
        logging.getLogger("agent").setLevel(logging.WARNING)
        logging.getLogger("llm").setLevel(logging.WARNING)
        logging.getLogger("tools").setLevel(logging.WARNING)

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Initialize LLM
    logger.info(f"Initializing LLM: {config.model_name}")
    llm = LLMInterface(
        api_key=config.gemini_api_key,
        model_name=config.model_name,
        temperature=config.temperature,
    )

    # Initialize tool manager and register tools
    logger.info("Registering tools...")
    tool_manager = ToolManager()

    # Register all available tools
    tool_manager.register_tool(
        SearchTool(
            api_key=config.serper_api_key,
            timeout=config.web_request_timeout,
        )
    )

    tool_manager.register_tool(
        ScrapeTool(
            timeout=config.web_request_timeout,
            max_length=config.max_tool_output_length,
        )
    )

    tool_manager.register_tool(
        CodeExecutorTool(
            timeout=config.code_execution_timeout,
            max_output_length=config.max_tool_output_length,
        )
    )

    tool_manager.register_tool(
        FileOpsTool(max_read_length=config.max_tool_output_length)
    )

    logger.info(f"Registered {len(tool_manager.get_all_tools())} tools")

    # Initialize agent
    agent = ReActAgent(
        llm=llm,
        tool_manager=tool_manager,
        max_iterations=config.max_iterations,
        max_tool_output_length=config.max_tool_output_length,
    )

    return agent


def write_results(output_file: str, results: List[dict]) -> None:
    """
    Write results to an output file.

    Args:
        output_file: Path to the output file
        results: List of result dictionaries
    """
    logger = logging.getLogger(__name__)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write("WEB RESEARCH AGENT RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")

            for i, result in enumerate(results, 1):
                f.write(f"\n{'=' * 100}\n")
                f.write(f"TASK {i}\n")
                f.write(f"{'=' * 100}\n\n")

                f.write(f"TASK DESCRIPTION:\n{result['task']}\n\n")
                f.write(f"{'-' * 100}\n\n")

                f.write(f"ANSWER:\n{result['answer']}\n\n")

                if result.get("error"):
                    f.write(f"ERROR: {result['error']}\n\n")

                f.write(
                    f"Execution time: {result.get('execution_time', 'N/A')} seconds\n"
                )
                f.write(f"Number of steps: {result.get('num_steps', 'N/A')}\n")

        logger.info(f"Results written to: {output_file}")

    except Exception as e:
        logger.error(f"Error writing results: {str(e)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web Research Agent - Run tasks using ReAct methodology"
    )

    parser.add_argument(
        "task_file",
        help="Path to file containing tasks (one task per line, separated by blank lines)",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="results.txt",
        help="Output file for results (default: results.txt)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("WEB RESEARCH AGENT")
    logger.info("=" * 80)

    # Read tasks
    tasks = read_tasks(args.task_file)

    if not tasks:
        logger.error("No tasks found in task file")
        sys.exit(1)

    # Initialize agent
    agent = initialize_agent(verbose=args.verbose)

    # Process each task
    results = []

    for i, task in enumerate(tasks, 1):
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"PROCESSING TASK {i}/{len(tasks)}")
        logger.info("=" * 80)
        logger.info(f"Task: {task[:100]}...")

        start_time = datetime.now()

        try:
            # Run the agent on the task
            answer = agent.run(task)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Get execution trace
            trace = agent.get_execution_trace()

            result = {
                "task": task,
                "answer": answer,
                "execution_time": execution_time,
                "num_steps": len(trace),
                "trace": trace,
            }

            logger.info(f"Task completed in {execution_time:.2f} seconds")
            logger.info(f"Number of steps: {len(trace)}")

        except Exception as e:
            logger.error(f"Error processing task: {str(e)}", exc_info=True)

            result = {
                "task": task,
                "answer": "Error occurred during processing",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "num_steps": 0,
            }

        results.append(result)

        # Print answer to console
        print("\n" + "=" * 80)
        print(f"TASK {i} ANSWER:")
        print("=" * 80)
        print(answer)
        print("=" * 80 + "\n")

    # Write results to file
    write_results(args.output, results)

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"COMPLETED ALL TASKS")
    logger.info(f"Total tasks: {len(tasks)}")
    logger.info(f"Results saved to: {args.output}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
