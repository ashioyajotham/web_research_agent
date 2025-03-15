from datetime import datetime
import re
from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

def extract_direct_answer(task_description: str, results: List[Dict[str, Any]], memory: Any) -> Optional[str]:
    """
    Extract a direct answer from research results for immediate display in the console.
    
    Args:
        task_description: The user's original question or task
        results: List of results from each step
        memory: Agent's memory object containing entities and other data
        
    Returns:
        str or None: A concise direct answer or None if no clear answer can be extracted
    """
    # Attempt to extract answer based on question type
    question_type = determine_question_type(task_description)
    
    # Handle "who is" questions using entity extraction
    if question_type == "who_is" and hasattr(memory, "extracted_entities"):
        # Check for relevant entities
        role_keyword = extract_role_from_question(task_description)
        org_keyword = extract_organization_from_question(task_description)
        
        # Try to find role information
        if role_keyword and "role" in memory.extracted_entities:
            for role in memory.extracted_entities["role"]:
                # For properly formatted roles (ROLE: Person @ Organization)
                if role_keyword.lower() in role.lower():
                    if ":" in role and "@" in role:
                        # Extract just what we need for a concise answer
                        parts = role.split(":")
                        if len(parts) >= 2:
                            return parts[0].strip() + " is " + parts[1].strip()
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
    
    # If no direct answer could be found, provide a generic response
    return None

def extract_role_from_question(question: str) -> Optional[str]:
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

def extract_organization_from_question(question: str) -> Optional[str]:
    """Extract the organization being asked about from a question."""
    question_lower = question.lower()
    
    # Pattern: "who is the X of Y" - extract Y
    org_pattern = r"(?:of|at|for)\s+([\w\s]+)(?:\?|$)"
    match = re.search(org_pattern, question_lower)
    if match:
        return match.group(1).strip()
    
    return None

def determine_question_type(question: str) -> str:
    """Determine the type of question being asked."""
    question_lower = question.lower()
    
    if question_lower.startswith("who is") or "who" in question_lower and "current" in question_lower:
        return "who_is"
    elif question_lower.startswith("what is") or question_lower.startswith("what are"):
        return "what_is"
    elif question_lower.startswith("when") or "date" in question_lower or "time" in question_lower:
        return "when"
    elif question_lower.startswith("where") or "location" in question_lower or "place" in question_lower:
        return "where"
    elif question_lower.startswith("how") and ("many" in question_lower or "much" in question_lower):
        return "quantity"
    else:
        return "general"

# Re-export the format_results function from the main formatters module
from utils.formatters.formatters import format_results