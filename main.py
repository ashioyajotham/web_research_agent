import argparse
import os
from agent.agent import WebResearchAgent

def process_tasks(task_file_path, output_dir="results"):
    """Process tasks from a file and write results to output directory."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Read tasks from file
    with open(task_file_path, "r") as f:
        tasks = [line.strip() for line in f if line.strip()]
    
    # Initialize agent
    agent = WebResearchAgent()
    
    # Process each task
    for i, task in enumerate(tasks):
        print(f"\n{'='*80}\nProcessing task {i+1}/{len(tasks)}: {task}\n{'='*80}")
        
        # Execute the task
        result = agent.execute_task(task)
        
        # Write result to file
        output_file = os.path.join(output_dir, f"task_{i+1}_result.md")
        with open(output_file, "w") as f:
            f.write(f"# Task: {task}\n\n")
            f.write(result)
        
        print(f"Task {i+1} completed. Result saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument("task_file", help="Path to text file containing tasks")
    parser.add_argument("--output", default="results", help="Output directory for results")
    args = parser.parse_args()
    
    process_tasks(args.task_file, args.output)
