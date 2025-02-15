import asyncio
import argparse
from typing import List, Tuple, Dict
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

from agent.planner import TaskPlanner
from agent.browser import WebBrowser
from agent.memory import Memory
from agent.comprehension import Comprehension
from models.llm import GeminiLLM
from utils.helpers import parse_task_file, Timer, logger, setup_logging, RichProgress, print_task_result, console

class WebResearchAgent:
    def __init__(self):
        self.llm = GeminiLLM()
        self.planner = TaskPlanner(self.llm)
        self.browser = WebBrowser()
        self.memory = Memory()
        self.comprehension = Comprehension(self.llm)
        self.timer = Timer()

    async def process_task(self, task: str) -> Tuple[str, List[Dict]]:
        """Process a single task and return the result with sources"""
        try:
            # Reset browser sources for new task
            self.browser.sources = []
            
            # Create execution plan
            plan = await self.planner.create_plan(task)
            logger.info(f"Created plan with {len(plan)} subtasks")

            # Execute subtasks
            while not self.planner.is_plan_completed():
                next_tasks = self.planner.get_next_tasks()
                for subtask in next_tasks:
                    result = await self._execute_subtask(subtask)
                    task_id = next(
                        k for k, v in self.planner.current_plan.items() 
                        if v == subtask
                    )
                    self.planner.update_task_status(task_id, "completed", result)
                    self.memory.store(f"{task}:{subtask.description}", result)
                    
            # Synthesize final response
            final_result = await self.comprehension.synthesize_results(
                self.memory.get_related(task)
            )
            return final_result, self.browser.sources

        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}")
            return f"Error processing task: {str(e)}", []

    async def _execute_subtask(self, subtask):
        """Execute a single subtask using appropriate tools"""
        try:
            for tool in subtask.tools_needed:
                if tool == "web_search":
                    return await self.browser.search(subtask.description)
                elif tool == "web_browse":
                    try:
                        return await self.browser.browse(subtask.description)
                    except UnicodeDecodeError:
                        logger.warning(f"Encoding issue with URL, trying alternative approach")
                        # Try to get content through search instead
                        search_results = await self.browser.search(subtask.description)
                        if search_results and 'organic' in search_results:
                            return search_results['organic'][0]['snippet']
                elif tool == "code_generation":
                    return await self.llm.generate_code(subtask.description)
            return "No appropriate tool found for subtask"
        except Exception as e:
            logger.error(f"Failed to execute subtask: {str(e)}")
            raise

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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed logging output"
    )
    args = parser.parse_args()

    # Initialize logging with verbosity level
    logger = setup_logging(verbose=args.verbose)
    
    # Initialize agent
    agent = WebResearchAgent()
    agent.timer.start()

    # Process tasks
    tasks = parse_task_file(args.task_file)
    results = []

    with RichProgress(verbose=args.verbose) as progress:
        task_processing = progress.add_task(
            "[cyan]Processing tasks...", 
            total=len(tasks)
        )
        
        for task in tasks:
            if args.verbose:
                console.print(f"\n[bold cyan]Processing task:[/] {task}")
            else:
                progress.update(
                    task_processing, 
                    description=f"[cyan]Processing: {task[:50]}..."
                )
            
            # Process task
            result, sources = await agent.process_task(task)
            results.append(f"Task: {task}\nResult: {result}\nSources: {json.dumps(sources, indent=2)}\n{'-'*50}")
            
            # Display result
            print_task_result(task, result, sources)
            
            # Update progress
            progress.advance(task_processing)

    # Write results
    output_path = Path(args.output)
    output_path.write_text("\n".join(results), encoding="utf-8")
    
    # Final summary
    console.print("\n[bold green]Task Processing Complete![/]")
    console.print(f"[dim]Time taken: {agent.timer.elapsed():.2f} seconds[/]")
    console.print(f"[dim]Results written to: {output_path}[/]")

if __name__ == "__main__":
    asyncio.run(main())