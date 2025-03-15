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
    Uses a flexible, multi-strategy approach to handle diverse question types.
    
    Args:
        task_description (str): The user's original question or task
        results (list): Results from each step
        memory (Memory): Agent's memory object containing entities and other data
        
    Returns:
        str or None: A concise direct answer or None if no clear answer can be extracted
    """
    # Try multiple strategies in order of preference
    
    # 1. Try entity-based extraction first (most precise)
    entity_answer = _extract_answer_from_entities(task_description, memory)
    if entity_answer:
        return entity_answer
    
    # 2. Try direct extraction from successful result outputs
    output_answer = _extract_answer_from_outputs(task_description, results)
    if output_answer:
        return output_answer
    
    # 3. Try search result snippets as a fallback
    snippet_answer = _extract_answer_from_snippets(task_description, memory)
    if snippet_answer:
        return snippet_answer
    
    # No answer could be extracted
    return None

def _extract_answer_from_entities(question: str, memory: Any) -> str:
    """Extract answers from entities based on question type."""
    if not hasattr(memory, "extracted_entities") or not memory.extracted_entities:
        return None
        
    # Analyze question to detect type and extract focus
    question_type = _determine_question_type(question.lower())
    focus_patterns = _extract_question_focus(question)
    
    # Handle person/organization questions
    if question_type == "who_is" or any(p in focus_patterns for p in ["person", "people", "individual"]):
        # Try to find relevant person entities
        if "person" in memory.extracted_entities and memory.extracted_entities["person"]:
            # Find best person match using question context
            person = _find_best_entity_match(memory.extracted_entities["person"], focus_patterns)
            
            # See if we also have organization context
            org = None
            if "organization" in memory.extracted_entities:
                org_candidates = memory.extracted_entities["organization"]
                org = _find_best_entity_match(org_candidates, focus_patterns)
            
            # See if we have role context
            role = None
            if "role" in memory.extracted_entities:
                role_candidates = memory.extracted_entities["role"]
                # Look for any role that contains both the person and organization
                for r in role_candidates:
                    if person.lower() in r.lower() and (not org or org.lower() in r.lower()):
                        # This role contains our person and org, extract structured info if possible
                        if ":" in r and "@" in r:
                            parts = r.split(":")
                            if len(parts) >= 2:
                                role_name = parts[0].strip()
                                return f"{person} is the {role_name} of {org}." if org else f"{person} is the {role_name}."
                        else:
                            role = r
                            break
            
            # Form answer based on available information
            if org and role:
                return f"{person} is the {role} of {org}."
            elif org:
                return f"{person} is associated with {org}."
            elif role:
                return f"{person} is the {role}."
            else:
                return f"{person} is the relevant person."
    
    # Handle definition questions
    elif question_type == "what_is" or any(p in focus_patterns for p in ["definition", "explain", "describe"]):
        # Look for relevant definition in entity descriptions
        if "definition" in memory.extracted_entities:
            return memory.extracted_entities["definition"][0]
            
        # Try to find definition from other entity types
        focus_entity = _find_best_entity_match(memory.extracted_entities.get("concept", []) + 
                                              memory.extracted_entities.get("organization", []), 
                                              focus_patterns)
        if focus_entity and "description" in memory.extracted_entities:
            for desc in memory.extracted_entities.get("description", []):
                if focus_entity.lower() in desc.lower():
                    return desc
    
    # Handle location questions
    elif question_type == "where" or any(p in focus_patterns for p in ["location", "place", "where"]):
        if "location" in memory.extracted_entities and memory.extracted_entities["location"]:
            location = _find_best_entity_match(memory.extracted_entities["location"], focus_patterns)
            return f"The location is {location}."
    
    # Handle date/time questions
    elif question_type == "when" or any(p in focus_patterns for p in ["date", "time", "when", "year"]):
        if "date" in memory.extracted_entities and memory.extracted_entities["date"]:
            date = _find_best_entity_match(memory.extracted_entities["date"], focus_patterns)
            return f"The date is {date}."
    
    # Handle quantity questions
    elif question_type == "quantity" or any(p in focus_patterns for p in ["how many", "how much", "percent", "number"]):
        for entity_type in ["percentage", "monetary_value", "number", "quantity"]:
            if entity_type in memory.extracted_entities and memory.extracted_entities[entity_type]:
                value = memory.extracted_entities[entity_type][0]
                return f"The value is {value}."
    
    # No suitable entity found
    return None

def _extract_answer_from_outputs(question: str, results: List[Dict[str, Any]]) -> str:
    """Extract direct answers from successful step outputs."""
    if not results:
        return None
        
    # Prioritize outputs from presentation tool as they're most likely to contain summaries
    present_results = [r for r in results if r.get("status") == "success" and 
                      r.get("step", "").lower().find("present") >= 0]
    
    # Analyze question to extract key terms for matching
    keywords = _extract_keywords_from_question(question)
    question_type = _determine_question_type(question.lower())
    
    # First try presentation results
    for result in present_results:
        output = result.get("output")
        if isinstance(output, str):
            # Extract paragraphs
            paragraphs = [p.strip() for p in output.split('\n\n') if p.strip()]
            # Look for paragraphs with high keyword density
            for para in paragraphs[:5]:  # Check first few paragraphs
                # Skip headings and very short/long paragraphs
                if para.startswith('#') or len(para) < 30 or len(para) > 300:
                    continue
                    
                # Count keyword matches
                keyword_matches = sum(1 for kw in keywords if kw.lower() in para.lower())
                if keyword_matches >= min(2, len(keywords)):  # At least 2 keywords or all if fewer
                    return para

    # If no presentation results, try other step outputs
    for result in reversed(results):  # Start from later results
        if result.get("status") != "success":
            continue
            
        output = result.get("output")
        # Handle string outputs
        if isinstance(output, str) and len(output) > 30:
            paragraphs = [p.strip() for p in output.split('\n\n') if p.strip()]
            for para in paragraphs[:3]:
                if len(para) > 30 and len(para) < 300 and not para.startswith('#'):
                    keyword_matches = sum(1 for kw in keywords if kw.lower() in para.lower())
                    if keyword_matches >= min(2, len(keywords)):
                        return para
        
        # Handle dict outputs with content field (browser results)
        elif isinstance(output, dict) and "content" in output:
            content = output["content"]
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            for para in paragraphs[:5]:
                if len(para) > 30 and len(para) < 300 and not para.startswith('#'):
                    keyword_matches = sum(1 for kw in keywords if kw.lower() in para.lower())
                    if keyword_matches >= min(2, len(keywords)):
                        return para
    
    return None

def _extract_answer_from_snippets(question: str, memory: Any) -> str:
    """Extract answers from search result snippets when other methods fail."""
    if not hasattr(memory, "search_results") or not memory.search_results:
        return None
        
    # Extract keywords for matching
    keywords = _extract_keywords_from_question(question)
    question_type = _determine_question_type(question.lower())
    
    # Combine snippets from top search results
    search_text = " ".join([r.get("snippet", "") for r in memory.search_results[:3]])
    
    # Try to find sentences with high keyword density
    sentences = re.split(r'[.!?]+', search_text)
    for sentence in sentences:
        sentence = sentence.strip()
        if 20 <= len(sentence) <= 200:  # Reasonable length for an answer
            # Count keyword matches
            keyword_matches = sum(1 for kw in keywords if kw.lower() in sentence.lower())
            if keyword_matches >= min(2, len(keywords)):
                # Ensure sentence ends with punctuation
                if not any(sentence.endswith(p) for p in ".!?"):
                    sentence += "."
                return sentence

    return None

def _find_best_entity_match(entities: List[str], focus_terms: List[str]) -> str:
    """Find the entity that best matches the focus terms."""
    if not entities:
        return None
        
    if not focus_terms:
        return entities[0]  # Return first entity if no focus terms
        
    # Score each entity based on how many focus terms it contains
    scores = []
    for entity in entities:
        entity_lower = entity.lower()
        score = sum(1 for term in focus_terms if term.lower() in entity_lower)
        scores.append((entity, score))
    
    # Return the entity with the highest score, or the first entity if no matches
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[0][0] if scores else entities[0]

def _extract_question_focus(question: str) -> List[str]:
    """Extract the key focus terms from a question."""
    # Remove common question words and conjunctions
    stop_words = {"what", "who", "when", "where", "how", "why", "is", "are", "was", "were", 
                 "will", "would", "should", "can", "could", "the", "a", "an", "of", "in", 
                 "on", "at", "by", "for", "with", "about", "to", "from", "as", "and", "or", "but"}
    
    # Split question into words
    words = [w.strip('?.,!;:()[]{}""\'\'')  for w in question.lower().split()]
    
    # Extract words that aren't stop words and are at least 3 chars long
    focus_terms = [w for w in words if w not in stop_words and len(w) >= 3]
    
    # Also extract quoted phrases if any
    quoted_patterns = re.findall(r'"([^"]*)"', question) + re.findall(r"'([^']*)'", question)
    focus_terms.extend(quoted_patterns)
    
    # Add noun phrases identified by basic patterns
    noun_phrases = []
    # Pattern: adjective + noun(s)
    adj_noun_pattern = r'\b([a-zA-Z]+ing|[a-zA-Z]+ed|[a-zA-Z]+ful|[a-zA-Z]+ive|[a-zA-Z]+al|[a-zA-Z]+ous|[a-zA-Z]+ary)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\b'
    for match in re.finditer(adj_noun_pattern, question, re.IGNORECASE):
        noun_phrases.append(match.group(0))
    
    # Pattern: noun + "of" + noun
    of_pattern = r'\b([a-zA-Z]+(?:\s+[a-zA-Z]+){0,2})\s+of\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,2})\b'
    for match in re.finditer(of_pattern, question, re.IGNORECASE):
        noun_phrases.append(match.group(0))
        
    # Add the noun phrases to focus terms
    focus_terms.extend(noun_phrases)
    
    return focus_terms

def _determine_question_type(question: str) -> str:
    """Determine the type of question using flexible pattern matching."""
    # More comprehensive patterns for question classification
    patterns = {
        "who_is": [r'who\s+(?:is|are|was|were)', r'whose', r'which person', r'identify the person'],
        "what_is": [r'what\s+(?:is|are|was|were)', r'define', r'describe', r'explain'],
        "when": [r'when\s+(?:is|are|was|were|did|will)', r'what time', r'what date', r'which year'],
        "where": [r'where\s+(?:is|are|was|were|did)', r'which place', r'location of', r'in which'],
        "why": [r'why\s+(?:is|are|was|were|did)', r'for what reason', r'what caused'],
        "how": [r'how\s+(?:to|is|are|was|were|did|can|could)', r'in what way', r'by what means'],
        "quantity": [r'how\s+(?:many|much)', r'what percentage', r'how frequently', r'what number']
    }
    
    question = question.lower()
    
    # Check each pattern category
    for q_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, question):
                return q_type
    
    # Additional keyword-based classification
    keywords = {
        "who_is": ["who", "person", "individual", "people", "team"],
        "what_is": ["what", "definition", "meaning", "describe", "explain"],
        "when": ["when", "date", "time", "year", "month", "day"],
        "where": ["where", "location", "place", "country", "city", "region"],
        "why": ["why", "reason", "cause", "purpose", "motivation"],
        "how": ["how", "method", "process", "technique", "way"],
        "quantity": ["many", "much", "percent", "number", "amount", "count"]
    }
    
    # Count keyword matches for each type
    scores = {q_type: 0 for q_type in keywords.keys()}
    for q_type, kw_list in keywords.items():
        for kw in kw_list:
            if kw in question:
                scores[q_type] += 1
    
    # Return the type with the highest score, default to "general"
    best_type = max(scores.items(), key=lambda x: x[1])
    return best_type[0] if best_type[1] > 0 else "general"

def _extract_keywords_from_question(question: str) -> List[str]:
    """Extract important keywords from a question using more advanced techniques."""
    # Expanded stop word list
    stop_words = {
        "the", "a", "an", "of", "in", "on", "at", "by", "for", "with", "to", "and", 
        "or", "but", "is", "are", "was", "were", "be", "been", "being", "have", 
        "has", "had", "do", "does", "did", "will", "would", "should", "can", "could", 
        "may", "might", "must", "shall", "need", "what", "who", "when", "where", 
        "why", "how", "which", "that", "this", "these", "those", "i", "you", "he", 
        "she", "it", "we", "they", "his", "her", "its", "our", "their", "about"
    }
    
    # Extract all words, excluding stop words and ensuring each word is at least 3 chars
    words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
    keywords = [w for w in words if w not in stop_words]
    
    # Extract quoted phrases as exact keywords
    quoted_phrases = re.findall(r'"([^"]*)"', question) + re.findall(r"'([^']*)'", question)
    keywords.extend(quoted_phrases)
    
    # Extract multi-word terms that might be important (noun phrases)
    noun_phrase_patterns = [
        r'\b[a-zA-Z]+\s+[a-zA-Z]+\s+[a-zA-Z]+\b',  # Three word phrases
        r'\b[a-zA-Z]+\s+[a-zA-Z]+\b'               # Two word phrases
    ]
    
    for pattern in noun_phrase_patterns:
        matches = re.findall(pattern, question.lower())
        for match in matches:
            # Check if this multi-word term is not just stop words
            words_in_phrase = match.split()
            non_stop_words = [w for w in words_in_phrase if w not in stop_words]
            if len(non_stop_words) > 0:
                keywords.append(match)
    
    # Weight keywords by position (earlier in question often more important)
    weighted_keywords = []
    for i, kw in enumerate(keywords):
        # Avoid duplicates and near-duplicates
        is_duplicate = False
        for existing_kw in weighted_keywords:
            if kw in existing_kw or existing_kw in kw:
                is_duplicate = True
                break
        if not is_duplicate:
            weighted_keywords.append(kw)
    
    return weighted_keywords
