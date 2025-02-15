import asyncio
import argparse
from typing import List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from agent.planner import TaskPlanner
from agent.browser import WebBrowser
from agent.memory import Memory
from agent.comprehension import Comprehension
from models.llm import GeminiLLM
from utils.helpers import parse_task_file, Timer, logger

class WebResearchAgent:
    def __init__(self):
        self.llm = GeminiLLM()
        self.planner = TaskPlanner(self.llm)
        self.browser = WebBrowser()
        self.memory = Memory()
        self.comprehension = Comprehension(self.llm)
        self.timer = Timer()

    async def process_task(self, task: str) -> str:
        """Process a single task and return the result"""
        try:
            # Create execution plan
            plan = await self.planner.create_plan(task)
            logger.info(f"Created plan with {len(plan)} subtasks")

            # Execute subtasks
            while not self.planner.is_plan_completed():
                next_tasks = self.planner.get_next_tasks()
                for subtask in next_tasks:
                    result = await self._execute_subtask(subtask)
                    self.memory.store(f"{task}:{subtask.description}", result)
                    
            # Synthesize final response
            final_result = await self.comprehension.synthesize_results(
                self.memory.get_related(task)
            )
            return final_result

        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}")
            return f"Error processing task: {str(e)}"

    async def _execute_subtask(self, subtask):
        """Execute a single subtask using appropriate tools"""
        for tool in subtask.tools_needed:
            if tool == "web_search":
                return await self.browser.search(subtask.description)
            elif tool == "web_browse":
                return await self.browser.browse(subtask.description)
            elif tool == "code_generation":
                return await self.llm.generate_code(subtask.description)
        return "No appropriate tool found for subtask"

async def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument(
        "task_file", 
        type=str,
        help="Path to file containing tasks"
    )
    parser.add_argument(
        "--output", 
        type=str,
        default="results.txt",
        help="Output file path"
    )
    args = parser.parse_args()

    # Initialize agent
    agent = WebResearchAgent()
    agent.timer.start()

    # Process tasks
    tasks = parse_task_file(args.task_file)
    results = []

    for task in tasks:
        logger.info(f"Processing task: {task}")
        result = await agent.process_task(task)
        results.append(f"Task: {task}\nResult: {result}\n{'-'*50}")

    # Write results
    output_path = Path(args.output)
    output_path.write_text("\n".join(results), encoding="utf-8")
    
    logger.info(f"Completed all tasks in {agent.timer.elapsed():.2f} seconds")
    logger.info(f"Results written to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())