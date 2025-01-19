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

async def process_tasks(task_file: Path, output_file: Path, config: Dict) -> None:
    agent = Agent(
        api_key=config['api_keys']['gemini'],
        serper_api_key=config['api_keys']['serper']
    )
    
    formatter = OutputFormatter()
    results = []
    
    tasks = [t for t in task_file.read_text().splitlines() if t.strip()]
    print(formatter.format_header())
    
    for i, task in enumerate(tasks, 1):
        print(formatter.format_task_section(i, len(tasks), task))
        print(f"Searching...")
        result = await agent.execute_task(task)
        print(formatter.format_search_results(result.get('results', [])))
        results.append(result)
    
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