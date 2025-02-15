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
        self.comprehension = Comprehension(self.llm)
        # Pass both llm and comprehension to TaskPlanner
        self.planner = TaskPlanner(self.llm, self.comprehension)
        self.browser = WebBrowser()
        self.memory = Memory()
        self.timer = Timer()

    async def process_task(self, task: str) -> Tuple[str, List[Dict]]:
        """Process task with dynamic handling based on task type"""
        try:
            self.browser.sources = []
            
            # Create execution plan
            plan = await self.planner.create_plan(task)
            logger.info(f"Created plan with {len(plan)} subtasks")

            # Track results with context
            task_results = {
                'type': self.comprehension.current_task_context.get('type'),
                'components': {},
                'sources': [],
                'validation': {}
            }

            # Execute subtasks
            while not self.planner.is_plan_completed():
                next_tasks = self.planner.get_next_tasks()
                for subtask in next_tasks:
                    result = await self._execute_subtask(subtask)
                    task_id = next(k for k, v in self.planner.current_plan.items() if v == subtask)
                    
                    # Store result with context
                    component = subtask.get('component', 'general')
                    if component not in task_results['components']:
                        task_results['components'][component] = []
                    task_results['components'][component].append(result)
                    
                    # Update task status
                    self.planner.update_task_status(task_id, "completed", result)
                    
            # Dynamic synthesis based on task type
            synthesis_prompt = f"""Synthesize results based on task type and requirements:

Task: {task}
Type: {task_results['type']}
Results: {json.dumps(task_results['components'], indent=2)}
Requirements: {json.dumps(self.comprehension.current_task_context.get('requirements', {}), indent=2)}

Create a response that:
1. Matches the task type's needs
2. Validates all requirements
3. Integrates component results appropriately
4. Highlights relationships between findings
5. Notes any gaps or uncertainties"""

            final_result = await self.llm.generate(synthesis_prompt)
            return final_result, self.browser.sources

        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}")
            return f"Error processing task: {str(e)}", []

    async def _execute_subtask(self, subtask):
        """Execute a single subtask using appropriate tools"""
        try:
            result = None
            for tool in subtask.tools_needed:
                if tool == "web_search":
                    result = await self.browser.search(subtask.description)
                elif tool == "web_browse":
                    # Only try to browse if description looks like a URL
                    if self.browser._is_valid_url(subtask.description):
                        result = await self.browser.browse(subtask.description)
                    else:
                        # Fall back to search for non-URL descriptions
                        search_result = await self.browser.search(subtask.description)
                        if search_result and 'organic' in search_result:
                            result = search_result['organic'][0]['snippet']
                elif tool == "code_generation":
                    result = await self.llm.generate_code(subtask.description)
                
                if result:
                    break
                    
            return result or f"No results found for: {subtask.description}"
            
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