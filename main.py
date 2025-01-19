import asyncio
import argparse
from pathlib import Path
from typing import List, Dict
import json
import sys

from agent.agent import Agent
from config.config_loader import ConfigLoader
from utils.helpers import setup_logging

async def process_tasks(task_file: Path, output_file: Path, config: Dict) -> None:
    # Initialize agent
    agent = Agent(config['api_keys']['gemini'])
    
    # Read tasks
    tasks = task_file.read_text().splitlines()
    
    # Process each task
    results = []
    for task in tasks:
        if task.strip():
            result = await agent.execute_task(task)
            results.append({
                'task': task,
                'result': result
            })
    
    # Save results
    output_file.write_text(json.dumps(results, indent=2))

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