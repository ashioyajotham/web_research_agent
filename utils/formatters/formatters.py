from typing import Dict, List, Any
import json
from config.config import get_config
import re

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

def extract_direct_answer(task_description: str, results: List[Dict[str, Any]], memory: Any) -> str:
    """
    Extract a direct answer from research results for immediate display in the console.
    
    Args:
        task_description (str): The user's original question or task
        results (list): Results from each step
        memory (Memory): Agent's memory object containing entities and other data
        
    Returns:
        str or None: A concise direct answer or None if no clear answer can be extracted
    """
    # Determine question type
    question_type = _determine_question_type(task_description.lower())
    
    # Handle "who is" questions using entity extraction
    if question_type == "who_is" and hasattr(memory, "extracted_entities"):
        # Extract role and organization from question
        role_keyword = _extract_role_from_question(task_description)
        org_keyword = _extract_organization_from_question(task_description)
        
        # Try to find role information
        if role_keyword and "role" in memory.extracted_entities:
            for role in memory.extracted_entities["role"]:
                # For properly formatted roles (ROLE: Person @ Organization)
                if role_keyword.lower() in role.lower():
                    if ":" in role and "@" in role:
                        # Extract just what we need for a concise answer
                        parts = role.split(":")
                        if len(parts) >= 2:
                            return f"{parts[0].strip()} is {parts[1].strip()}"
                    else:
                        return role
        
        # Fall back to person + organization if available
        if "person" in memory.extracted_entities and len(memory.extracted_entities["person"]) > 0:
            person = memory.extracted_entities["person"][0]
            
            # Try to connect person with organization
            if org_keyword and "organization" in memory.extracted_entities:
                for org in memory.extracted_entities["organization"]:
                    if org_keyword.lower() in org.lower():
                        if role_keyword:
                            return f"The {role_keyword} of {org} is {person}."
                        else:
                            return f"{person} is associated with {org}."
            
            # If no organization match but we have a role
            if role_keyword:
                # Try to use memory's role lookup
                if hasattr(memory, "find_entity_by_role"):
                    person_name, org_name = memory.find_entity_by_role(role_keyword)
                    if person_name:
                        if org_name:
                            return f"The {role_keyword} of {org_name} is {person_name}."
                        else:
                            return f"The {role_keyword} is {person_name}."
    
    # For "what is" questions about facts
    if question_type == "what_is":
        # Try to extract definitions or explanations from presentation output
        for result in reversed(results):
            if result.get("status") == "success" and result.get("output"):
                output = result.get("output")
                if isinstance(output, str) and len(output) > 30:
                    # Extract first paragraph that looks like a definition
                    paragraphs = output.split('\n\n')
                    for para in paragraphs[:3]:  # Check first few paragraphs
                        if len(para) > 30 and len(para) < 300 and not para.startswith('#'):
                            return para
    
    # If no direct answer could be extracted
    return None

def _extract_role_from_question(question: str) -> str:
    """Extract the role being asked about from a question."""
    # Common role keywords
    common_roles = [
        "ceo", "chief executive officer", "cfo", "chief financial officer", 
        "coo", "chief operating officer", "president", "founder", "director",
        "chairman", "chairperson", "head", "leader", "manager"
    ]
    
    question_lower = question.lower()
    
    # Check for common patterns: "who is the X of Y"
    role_pattern = r"who\s+is\s+(?:the|a)?\s+([\w\s]+?)(?:\s+of|\s+at|\s+for|\s+in|\?|$)"
    match = re.search(role_pattern, question_lower)
    if match:
        role = match.group(1).strip()
        return role
    
    # Check for specific role mentions
    for role in common_roles:
        if role in question_lower:
            return role
    
    return None

def _extract_organization_from_question(question: str) -> str:
    """Extract the organization being asked about from a question."""
    question_lower = question.lower()
    
    # Pattern: "who is the X of Y" - extract Y
    org_pattern = r"(?:of|at|for)\s+([\w\s]+)(?:\?|$)"
    match = re.search(org_pattern, question_lower)
    if match:
        return match.group(1).strip()
    
    return None

def _determine_question_type(question: str) -> str:
    """Determine the type of question being asked."""
    if question.startswith("who is") or "who" in question and "current" in question:
        return "who_is"
    elif question.startswith("what is") or question.startswith("what are"):
        return "what_is"
    elif question.startswith("when") or "date" in question or "time" in question:
        return "when"
    elif question.startswith("where") or "location" in question or "place" in question:
        return "where"
    elif question.startswith("how") and ("many" in question or "much" in question):
        return "quantity"
    else:
        return "general"
