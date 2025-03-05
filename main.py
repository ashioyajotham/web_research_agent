import argparse
import os
from agent.agent import WebResearchAgent
from utils.console_ui import (
    console, configure_logging, display_title, display_task_header,
    create_progress_context, display_plan, display_result, display_completion_message
)

def process_tasks(task_file_path, output_dir="results"):
    """Process tasks from a file and write results to output directory."""
    # Configure rich logging
    configure_logging()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Display title
    display_title("Web Research Agent")
    
    # Read tasks from file
    with open(task_file_path, "r") as f:
        tasks = [line.strip() for line in f if line.strip()]
    
    console.print(f"[bold]Loaded {len(tasks)} tasks from {task_file_path}[/]")
    
    # Initialize agent
    agent = WebResearchAgent()
    
    # Process each task
    for i, task in enumerate(tasks):
        display_task_header(i+1, len(tasks), task)
        
        # Create a plan
        with console.status("[bold blue]Planning...", spinner="dots"):
            # This will trigger task analysis and planning
            # But we'll capture the actual execution inside our progress context
            agent.memory.add_task(task)
            task_analysis = agent.comprehension.analyze_task(task)
            plan = agent.planner.create_plan(task, task_analysis)
        
        # Display the plan
        display_plan([{"description": step.description, "tool": step.tool_name} for step in plan.steps])
        
        # Execute the task with progress tracking
        results = []
        with create_progress_context() as progress:
            task_progress = progress.add_task("Executing task...", total=len(plan.steps))
            
            for step_index, step in enumerate(plan.steps):
                progress.update(task_progress, description=f"Step {step_index+1}: {step.description[:30]}...")
                
                # Get the appropriate tool
                tool = agent.tool_registry.get_tool(step.tool_name)
                if not tool:
                    error_msg = f"Tool '{step.tool_name}' not found"
                    results.append({"step": step.description, "status": "error", "output": error_msg})
                    progress.update(task_progress, advance=1)
                    continue
                
                # Prepare parameters with variable substitution
                parameters = agent._substitute_parameters(step.parameters, results)
                
                # Execute the tool
                try:
                    output = tool.execute(parameters, agent.memory)
                    results.append({"step": step.description, "status": "success", "output": output})
                    agent.memory.add_result(step.description, output)
                    
                    # Store search results specifically for easy reference
                    if step.tool_name == "search" and isinstance(output, dict) and "results" in output:
                        agent.memory.search_results = output["results"]
                except Exception as e:
                    results.append({"step": step.description, "status": "error", "output": str(e)})
                
                # Display the result of this step
                display_result(step_index+1, step.description, results[-1]["status"], results[-1]["output"])
                
                # Update progress
                progress.update(task_progress, advance=1)
        
        # Format the results
        formatted_results = agent._format_results(task, plan, results)
        
        # Write result to file
        output_file = os.path.join(output_dir, f"task_{i+1}_result.md")
        with open(output_file, "w") as f:
            f.write(f"# Task: {task}\n\n")
            f.write(formatted_results)
        
        # Display completion message
        display_completion_message(task, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument("task_file", help="Path to text file containing tasks")
    parser.add_argument("--output", default="results", help="Output directory for results")
    args = parser.parse_args()
    
    process_tasks(args.task_file, args.output)
