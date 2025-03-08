from typing import Dict, List, Any
import json
from config.config import get_config

def _truncate_content(content, max_length=2000):
    """Truncate content to a maximum length."""
    if not content or len(content) <= max_length:
        return content
    
    return content[:max_length] + f"... [Content truncated, {len(content) - max_length} more characters]"

def format_results(task_description: str, plan: Any, results: List[Dict[str, Any]]) -> str:
    """
    Format the results of a task into a well-structured output.
    
    Args:
        task_description (str): Original task description
        plan (Plan): The plan that was executed
        results (list): Results from each step of the plan
        
    Returns:
        str: Formatted results
    """
    config = get_config()
    output_format = config.get("output_format", "markdown").lower()
    
    if output_format == "json":
        return _format_as_json(task_description, plan, results)
    elif output_format == "html":
        return _format_as_html(task_description, plan, results)
    else:  # Default to markdown
        return _format_as_markdown(task_description, plan, results)

def _format_as_markdown(task_description: str, plan: Any, results: List[Dict[str, Any]]) -> str:
    """Format results as Markdown."""
    output = [
        f"# Research Results: {task_description}",
        "\n## Plan\n"
    ]
    
    # Add plan details
    for i, step in enumerate(plan.steps):
        output.append(f"{i+1}. **{step.description}** (using {step.tool_name})")
    
    output.append("\n## Results\n")
    
    # Add results for each step
    for i, result in enumerate(results):
        step_desc = result.get("step", f"Step {i+1}")
        status = result.get("status", "unknown")
        step_output = result.get("output", "")
        
        output.append(f"### {i+1}. {step_desc}")
        output.append(f"**Status**: {status}")
        
        # Format output based on status
        if status == "error":
            # Format error message clearly
            error_msg = step_output if isinstance(step_output, str) else str(step_output)
            output.append(f"\n**Error**: {error_msg}\n")
            continue
        
        # Format the output based on the type
        if isinstance(step_output, dict):
            if "error" in step_output:
                # This is an error result that wasn't caught earlier
                output.append(f"\n**Error**: {step_output['error']}\n")
            elif "content" in step_output:  # Browser results
                output.append(f"\n**Source**: [{step_output.get('title', 'Web content')}]({step_output.get('url', '#')})\n")
                output.append(f"\n{_truncate_content(step_output['content'], 2000)}\n")
            elif "results" in step_output:  # Search results
                output.append(f"\n**Search Query**: {step_output.get('query', 'Unknown query')}")
                output.append(f"**Found**: {step_output.get('result_count', 0)} results\n")
                
                for j, search_result in enumerate(step_output.get('results', [])):
                    output.append(f"{j+1}. [{search_result.get('title', 'No title')}]({search_result.get('link', '#')})")
                    output.append(f"   {search_result.get('snippet', 'No description')}\n")
            else:
                # Generic dictionary output
                output.append("\n```json")
                output.append(json.dumps(step_output, indent=2))
                output.append("```\n")
        elif isinstance(step_output, str):
            if step_output.startswith("```") or step_output.startswith("# "):
                # Already formatted markdown
                output.append(f"\n{step_output}\n")
            else:
                output.append(f"\n{step_output}\n")
        else:
            # Convert other types to string
            output.append(f"\n{str(step_output)}\n")
    
    output.append("\n## Summary\n")
    output.append("The agent has completed the research task. Please review the results above.")
    
    return "\n".join(output)

def _format_as_json(task_description: str, plan: Any, results: List[Dict[str, Any]]) -> str:
    """Format results as JSON."""
    output = {
        "task": task_description,
        "plan": [
            {
                "description": step.description,
                "tool": step.tool_name,
                "parameters": step.parameters
            }
            for step in plan.steps
        ],
        "results": results,
        "summary": "The agent has completed the research task."
    }
    
    return json.dumps(output, indent=2)

def _format_as_html(task_description: str, plan: Any, results: List[Dict[str, Any]]) -> str:
    """Format results as HTML."""
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        f"<title>Research Results: {task_description}</title>",
        """<style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #333; }
        pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
        .error { color: #dc3545; }
        .result-item { border-bottom: 1px solid #ddd; padding-bottom: 15px; margin-bottom: 15px; }
        .search-result { margin-left: 20px; }
        </style>""",
        "</head>",
        "<body>",
        f"<h1>Research Results: {task_description}</h1>",
        "<h2>Plan</h2>",
        "<ol>"
    ]
    
    # Add plan details
    for step in plan.steps:
        html.append(f"<li><strong>{step.description}</strong> (using {step.tool_name})</li>")
    
    html.append("</ol>")
    html.append("<h2>Results</h2>")
    
    # Add results for each step
    for i, result in enumerate(results):
        step_desc = result.get("step", f"Step {i+1}")
        status = result.get("status", "unknown")
        step_output = result.get("output", {})
        
        html.append(f"<div class='result-item'>")
        html.append(f"<h3>{i+1}. {step_desc}</h3>")
        html.append(f"<p><strong>Status</strong>: {status}</p>")
        
        if status == "error":
            html.append(f"<p class='error'><strong>Error</strong>: {step_output}</p>")
            html.append("</div>")
            continue
        
        # Format the output based on the type
        if isinstance(step_output, dict):
            if "error" in step_output:
                html.append(f"<p class='error'><strong>Error</strong>: {step_output['error']}</p>")
            elif "content" in step_output:  # Browser results
                html.append(f"<p><strong>Source</strong>: <a href='{step_output.get('url', '#')}'>{step_output.get('title', 'Web content')}</a></p>")
                content = step_output['content'].replace("\n", "<br>")
                html.append(f"<div>{_truncate_content(content, 2000)}</div>")
            elif "results" in step_output:  # Search results
                html.append(f"<p><strong>Search Query</strong>: {step_output.get('query', 'Unknown query')}</p>")
                html.append(f"<p><strong>Found</strong>: {step_output.get('result_count', 0)} results</p>")
                
                html.append("<ol>")
                for search_result in step_output.get('results', []):
                    html.append("<li class='search-result'>")
                    html.append(f"<a href='{search_result.get('link', '#')}'>{search_result.get('title', 'No title')}</a>")
                    html.append(f"<p>{search_result.get('snippet', 'No description')}</p>")
                    html.append("</li>")
                html.append("</ol>")
            else:
                # Generic dictionary output
                html.append("<pre>")
                html.append(json.dumps(step_output, indent=2))
                html.append("</pre>")
        elif isinstance(step_output, str):
            if step_output.startswith("```") or step_output.startswith("# "):
                # Already formatted markdown
                html.append(f"<pre>{step_output}</pre>")
            else:
                html.append(f"<p>{step_output}</p>")
        else:
            # Convert other types to string
            html.append(f"<p>{str(step_output)}</p>")
        
        html.append("</div>")
    
    html.append("<h2>Summary</h2>")
    html.append("<p>The agent has completed the research task. Please review the results above.</p>")
    html.append("</body>")
    html.append("</html>")
    
    return "\n".join(html)
