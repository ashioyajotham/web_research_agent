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
        """Process task with improved task status tracking"""
        try:
            # Reset state
            self.browser.sources = []
            results_cache = []
            
            # Phase 1: Understanding
            task_context = await self.comprehension._understand_task(task)
            
            # Phase 2: Planning
            plan = await self.planner.create_plan(task)
            logger.info(f"Created plan with {len(plan)} subtasks")
            
            # Phase 3: Execution with status tracking
            while not self.planner.is_plan_completed():
                next_tasks = self.planner.get_next_tasks()
                
                if not next_tasks:
                    logger.info("No new tasks to process, moving to next phase")
                    break
                
                # Execute tasks in parallel
                tasks = [self._execute_subtask(task, task_context) for task in next_tasks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle results and update task status
                for task_def, result in zip(next_tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"Task failed: {str(result)}")
                        self.planner.update_task_status(task_def['id'], {
                            'completed': True,
                            'success': False,
                            'error': str(result)
                        })
                        continue
                    
                    # Store successful result
                    results_cache.append(result)
                    self.memory.store(f"{task}:{task_def['description']}", result)
                    
                    # Update task status
                    self.planner.update_task_status(task_def['id'], {
                        'completed': True,
                        'success': True,
                        'result': result
                    })
                
                # Rate limiting pause
                await asyncio.sleep(1)
            
            # Phase 4: Synthesis
            return await self.comprehension.synthesize_results(results_cache), self.browser.sources

        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}")
            return f"Error processing task: {str(e)}", []

    async def _execute_subtask(self, task_def: Dict, task_context: Dict):
        """Execute subtask with improved error handling"""
        try:
            task_type = task_def.get('type', 'search')
            result = None
            
            if task_type == 'search':
                result = await self.browser.search(
                    task_def['description'],
                    task_context
                )
            elif task_type == 'analysis':
                result = await self.comprehension.analyze_results(
                    task_def['description'],
                    task_context
                )
            elif task_type == 'synthesis':
                result = await self.comprehension.synthesize_partial(
                    task_def['description'],
                    task_context
                )
            
            return result or f"No results found for: {task_def['description']}"
            
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