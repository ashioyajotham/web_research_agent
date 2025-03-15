from datetime import datetime
import json

class Memory:
    """Memory system for the agent to store and retrieve information."""
    
    def __init__(self):
        """Initialize the memory system."""
        self.current_task = None
        self.task_results = {}
        self.past_tasks = []
        self.web_content_cache = {}
        self.conversation_history = []
        self.search_results = []  # Store search results directly
        self.extracted_entities = {} # New property to track extracted entities
    
    def add_task(self, task_description):
        """
        Add a new task to memory.
        
        Args:
            task_description (str): Description of the task
        """
        if self.current_task:
            self.past_tasks.append({
                "task": self.current_task,
                "results": self.task_results.copy(),
                "timestamp": datetime.now().isoformat()
            })
            
        self.current_task = task_description
        self.task_results = {}
        self.conversation_history.append({
            "role": "system",
            "content": f"New task: {task_description}"
        })
    
    def add_result(self, step_description, result):
        """
        Add a result for a step in the current task.
        
        Args:
            step_description (str): Description of the step
            result (any): Result from the step execution
        """
        self.task_results[step_description] = result
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Completed: {step_description}"
        })
    
    def cache_web_content(self, url, content, metadata=None):
        """
        Cache web content to avoid redundant fetching.
        
        Args:
            url (str): URL of the web page
            content (str): Content of the web page
            metadata (dict, optional): Additional metadata about the content
        """
        self.web_content_cache[url] = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
    
    def get_cached_content(self, url):
        """
        Get cached content for a URL if available.
        
        Args:
            url (str): URL to check for cached content
            
        Returns:
            dict or None: Cached content or None if not cached
        """
        return self.web_content_cache.get(url)
    
    def get_conversation_context(self, max_tokens=8000):
        """
        Get recent conversation history for context.
        
        Args:
            max_tokens (int): Approximate maximum tokens to include
            
        Returns:
            list: Recent conversation history
        """
        # This is a simplified version. In a real implementation,
        # we would count tokens and truncate the history appropriately
        return self.conversation_history[-10:]
    
    def get_relevant_past_tasks(self, query, max_results=3):
        """
        Find past tasks that might be relevant to the current query.
        
        Args:
            query (str): Query to match against past tasks
            max_results (int): Maximum number of results to return
            
        Returns:
            list: Relevant past tasks
        """
        # Simple keyword matching for now
        # In a real implementation, we would use semantic search
        matches = []
        for past_task in self.past_tasks:
            if any(word in past_task["task"].lower() for word in query.lower().split()):
                matches.append(past_task)
                if len(matches) >= max_results:
                    break
        return matches

    def add_entities(self, entities):
        """
        Add or update extracted entities in memory intelligently.
        
        Args:
            entities (dict): Dictionary of entity types and values
        """
        # For each entity type
        for entity_type, values in entities.items():
            if entity_type not in self.extracted_entities:
                self.extracted_entities[entity_type] = []
            
            # Add new unique entities with deduplication
            for value in values:
                # Skip very short entities as they're often false positives
                if len(str(value)) < 3:
                    continue
                    
                # Check if this or a similar entity already exists
                exists = False
                value_lower = value.lower()
                
                for existing in self.extracted_entities[entity_type]:
                    # Check for exact match or if one contains the other
                    if (existing.lower() == value_lower or 
                        existing.lower() in value_lower or 
                        value_lower in existing.lower()):
                        exists = True
                        break
                
                if not exists:
                    self.extracted_entities[entity_type].append(value)

    def update_entities(self, entities):
        """
        Update entities with priority information (replace entire entity list).
        
        Args:
            entities (dict): Dictionary of entity types and values to update
        """
        for entity_type, values in entities.items():
            self.extracted_entities[entity_type] = values

    def find_entity_by_role(self, role_name):
        """
        Find a person entity associated with a specific role.
        
        Args:
            role_name (str): Role name to search for (e.g., "CEO", "founder")
            
        Returns:
            tuple: (person_name, organization_name) or (None, None) if not found
        """
        if "role" not in self.extracted_entities:
            return None, None
            
        role_name = role_name.lower()
        
        # Look through all roles for a match
        for role in self.extracted_entities["role"]:
            if role_name in role.lower():
                # Parse the role if it's in the format "Role: Person @ Organization"
                if ":" in role and "@" in role:
                    parts = role.split(":")
                    if len(parts) >= 2:
                        person_org = parts[1].strip().split("@")
                        if len(person_org) >= 2:
                            person = person_org[0].strip()
                            org = person_org[1].strip()
                            return person, org
                # Return just the role if it doesn't follow the format
                return role, None
        
        return None, None

    def get_related_entities(self, entity_value):
        """
        Find related entities across different entity types.
        
        Args:
            entity_value (str): Entity value to find relationships for
            
        Returns:
            dict: Dictionary of related entities by type
        """
        related = {}
        entity_value_lower = entity_value.lower()
        
        for entity_type, values in self.extracted_entities.items():
            related_entities = []
            
            for value in values:
                # For roles, check if the entity is mentioned in the role
                if entity_type == "role" and entity_value_lower in value.lower():
                    related_entities.append(value)
                # For complex role entries like "CEO: John @ Acme"
                elif ":" in value and "@" in value:
                    parts = value.split("@")
                    if len(parts) >= 2:
                        role_org = parts[1].strip()
                        if entity_value_lower in role_org.lower():
                            related_entities.append(value)
            
            if related_entities:
                related[entity_type] = related_entities
        
        return related

    def get_entities(self, entity_type=None):
        """
        Get extracted entities from memory.
        
        Args:
            entity_type (str, optional): Type of entity to retrieve
                If None, return all entity types
                
        Returns:
            dict or list: Extracted entities
        """
        if entity_type:
            return self.extracted_entities.get(entity_type, [])
        return self.extracted_entities

    def get_results(self):
        """
        Get all results from the current task.
        
        Returns:
            list: List of result dictionaries
        """
        # Convert task_results dict to a list of dicts with step info
        results = []
        for step_desc, output in self.task_results.items():
            results.append({
                "step": step_desc,
                "status": "success" if output else "error", 
                "output": output
            })
        return results

    def get_search_snippet_content(self, max_results=5):
        """
        Get content derived from search snippet results as fallback when browsing fails.
        
        Args:
            max_results (int): Maximum number of search results to include
            
        Returns:
            str: Combined content from search snippets
        """
        if not hasattr(self, 'search_results') or not self.search_results:
            return "No search results available."
        
        combined_text = []
        
        # Add each search result as a section
        for i, result in enumerate(self.search_results[:max_results]):
            if i >= max_results:
                break
                
            title = result.get("title", f"Result {i+1}")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            
            result_text = f"### {title}\n{snippet}\nSource: {link}\n"
            combined_text.append(result_text)
        
        return "\n".join(combined_text)
