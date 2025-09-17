import argparse
import os
import asyncio
from agent.agent import WebResearchAgent
from utils.console_ui import (
    console, configure_logging, display_title, display_task_header,
    create_progress_context, display_plan, display_result, display_completion_message
)
from utils.logger import get_logger
from utils.task_parser import parse_tasks_from_file

# Initialize the logger 
logger = get_logger(__name__)

async def process_tasks(task_file_path, output_dir="results"):
    """Process tasks from a file and write results to output directory."""
    # Configure rich logging
    configure_logging()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Display title
    display_title("Web Research Agent")
    
    # Read tasks from file using the new parser
    tasks = parse_tasks_from_file(task_file_path)
    
    console.print(f"[bold]Loaded {len(tasks)} tasks from {task_file_path}[/]")
    
    # Initialize agent
    agent = WebResearchAgent()
    
    # Process each task
    for i, task in enumerate(tasks):
        display_task_header(i+1, len(tasks), task)
        
        try:
            # Use the agent's run method instead of manual orchestration
            result = await agent.run(task)
            
            # Save the result
            result_filename = os.path.join(output_dir, f"task_{i+1}_result.md")
            
            with open(result_filename, 'w', encoding='utf-8') as result_file:
                result_file.write(result)
            
            display_completion_message(i+1, len(tasks))
            
        except Exception as e:
            logger.error(f"Error processing task {i+1}: {e}")
            # Save error result
            error_result = f"# Task {i+1} - Error\n\nAn error occurred while processing this task:\n\n```\n{str(e)}\n```"
            result_filename = os.path.join(output_dir, f"task_{i+1}_result.md")
            
            with open(result_filename, 'w', encoding='utf-8') as result_file:
                result_file.write(error_result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument("task_file", help="Path to text file containing tasks")
    parser.add_argument("--output", default="results", help="Output directory for results")
    args = parser.parse_args()
    
    asyncio.run(process_tasks(args.task_file, args.output))
