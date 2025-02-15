import asyncio
import argparse
from pathlib import Path
from typing import List, Dict
import json
import sys
import logging
from colorama import Fore, Style

from agent.agent import Agent
from config.config_loader import ConfigLoader
from utils.helpers import setup_logging
from utils.formatters.output_formatter import OutputFormatter
from utils.task_parser import TaskParser

async def process_tasks(task_file: Path, output_file: Path, config: Dict) -> None:
    agent = Agent(
        api_key=config['api_keys']['gemini'],
        serper_api_key=config['api_keys']['serper']
    )
    
    formatter = OutputFormatter()
    parser = TaskParser()
    results = []
    
    content = task_file.read_text()
    tasks = parser.parse_tasks(content)
    print(formatter.format_header())
    
    for i, task_data in enumerate(tasks, 1):
        try:
            full_task = task_data['task']
            if task_data['subtasks']:
                subtasks_text = "\n    ".join(task_data['subtasks'])
                full_task += f"\nCriteria:\n    {subtasks_text}"
            
            print(formatter.format_task_section(i, len(tasks), task_data['task']))
            if task_data['subtasks']:
                for subtask in task_data['subtasks']:
                    print(f"    • {subtask}")
                    
            result = await agent.execute_task(full_task)
            if result['success']:
                print(formatter.format_search_results(result.get('results', [])))
            else:
                print(formatter._format_error(result.get('error', 'Unknown error occurred')))
            results.append(result)
        except Exception as e:
            print(formatter._format_error(f"Error processing task {i}: {str(e)}"))
            continue
    
    output_file.write_text(json.dumps({"searches": results}, indent=2))

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='LLM Agent Task Processor')
    parser.add_argument('task_file', type=Path, help='Path to file containing tasks')
    parser.add_argument('--output', type=Path, default=Path('results.json'),
                      help='Path to output file')
    parser.add_argument('--config', type=Path, default=Path('config/config.yaml'),
                      help='Path to config file')
    args = parser.parse_args()

    # Validate task file
    if not args.task_file.exists():
        print(f"Task file not found: {args.task_file}")
        sys.exit(1)

    # Load configuration
    config = ConfigLoader(args.config).config
    
    # Setup logging
    logger = setup_logging(config)
    
    try:
        # Run task processing
        asyncio.run(process_tasks(args.task_file, args.output, config))
        logger.info(f"Results saved to {args.output}")
        
    except Exception as e:
        logger.error(f"Error processing tasks: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()