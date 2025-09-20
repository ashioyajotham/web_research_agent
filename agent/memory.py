from datetime import datetime
import json
import re
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass

@dataclass
class EntityMention:
    """Represents a mention of an entity in a specific context."""
    source_url: str
    context: str
    timestamp: str
    confidence: float = 1.0
    mention_type: str = "direct"  # direct, indirect, inferred

@dataclass
class ResearchEntity:
    """Represents an entity discovered during research."""
    name: str
    entity_type: str  # person, organization, event, statement, date, location, etc.
    confidence: float
    mentions: List[EntityMention]
    attributes: Dict[str, Any]  # Dynamic attributes like role, date, location
    aliases: Set[str]  # Alternative names/references
    
    def __post_init__(self):
        if not self.mentions:
            self.mentions = []
        if not self.attributes:
            self.attributes = {}
        if not self.aliases:
            self.aliases = set()

class ResearchKnowledgeGraph:
    """Knowledge graph for tracking entities and relationships during research."""
    
    def __init__(self):
        self.entities: Dict[str, ResearchEntity] = {}  # entity_id -> ResearchEntity
        self.entity_index: Dict[str, List[str]] = {}  # name -> [entity_ids] for fuzzy matching
        self.relationships: Dict[Tuple[str, str], Dict[str, Any]] = {}  # (entity1_id, entity2_id) -> relationship_info
        self.source_entities: Dict[str, List[str]] = {}  # source_url -> [entity_ids]
        self.temporal_events: List[Dict[str, Any]] = []  # Chronological events
        
    def _generate_entity_id(self, name: str, entity_type: str) -> str:
        """Generate a unique entity ID."""
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).replace(' ', '_').lower()
        return f"{entity_type}_{clean_name}_{len(self.entities)}"
    
    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for comparison."""
        return re.sub(r'[^\w\s]', '', name.lower().strip())
    
    def find_similar_entities(self, name: str, entity_type: str) -> List[str]:
        """Find entities with similar names."""
        normalized = self._normalize_name(name)
        candidates = []
        
        for entity_id, entity in self.entities.items():
            if entity.entity_type == entity_type:
                if normalized in self._normalize_name(entity.name) or self._normalize_name(entity.name) in normalized:
                    candidates.append(entity_id)
                # Check aliases
                for alias in entity.aliases:
                    if normalized in self._normalize_name(alias) or self._normalize_name(alias) in normalized:
                        candidates.append(entity_id)
                        break
        
        return candidates
    
    def add_entity_mention(self, entity_name: str, entity_type: str, source_url: str, 
                          context: str, attributes: Dict[str, Any] = None, 
                          confidence: float = 1.0) -> str:
        """Add or update an entity mention with smart resolution."""
        # Find existing similar entities
        similar_entities = self.find_similar_entities(entity_name, entity_type)
        
        if similar_entities:
            # Use the most confident existing entity
            entity_id = similar_entities[0]
            entity = self.entities[entity_id]
            
            # Add alias if name is different
            if self._normalize_name(entity_name) != self._normalize_name(entity.name):
                entity.aliases.add(entity_name)
            
            # Update confidence (weighted average)
            total_mentions = len(entity.mentions) + 1
            entity.confidence = (entity.confidence * len(entity.mentions) + confidence) / total_mentions
        else:
            # Create new entity
            entity_id = self._generate_entity_id(entity_name, entity_type)
            entity = ResearchEntity(
                name=entity_name,
                entity_type=entity_type,
                confidence=confidence,
                mentions=[],
                attributes=attributes or {},
                aliases=set()
            )
            self.entities[entity_id] = entity
            
            # Update entity index
            normalized = self._normalize_name(entity_name)
            if normalized not in self.entity_index:
                self.entity_index[normalized] = []
            self.entity_index[normalized].append(entity_id)
        
        # Add mention
        mention = EntityMention(
            source_url=source_url,
            context=context,
            timestamp=datetime.now().isoformat(),
            confidence=confidence
        )
        entity.mentions.append(mention)
        
        # Update source index
        if source_url not in self.source_entities:
            self.source_entities[source_url] = []
        if entity_id not in self.source_entities[source_url]:
            self.source_entities[source_url].append(entity_id)
        
        # Update attributes
        if attributes:
            for key, value in attributes.items():
                if key not in entity.attributes:
                    entity.attributes[key] = value
                elif isinstance(entity.attributes[key], list):
                    if value not in entity.attributes[key]:
                        entity.attributes[key].append(value)
                else:
                    # Convert to list if multiple values
                    if entity.attributes[key] != value:
                        entity.attributes[key] = [entity.attributes[key], value]
        
        return entity_id
    
    def link_entities(self, entity1_id: str, entity2_id: str, relationship_type: str, 
                     source_url: str, confidence: float = 1.0, metadata: Dict[str, Any] = None):
        """Create or update a relationship between entities."""
        relationship_key = (entity1_id, entity2_id)
        if relationship_key not in self.relationships:
            self.relationships[relationship_key] = {
                "type": relationship_type,
                "confidence": confidence,
                "sources": [source_url],
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Update existing relationship
            rel = self.relationships[relationship_key]
            if source_url not in rel["sources"]:
                rel["sources"].append(source_url)
            # Update confidence (weighted average)
            rel["confidence"] = (rel["confidence"] + confidence) / 2
            if metadata:
                rel["metadata"].update(metadata)
    
    def get_entity_timeline(self, entity_name: str) -> List[Dict[str, Any]]:
        """Get chronological timeline of entity mentions."""
        entity_id = self._find_entity_by_name(entity_name)
        if not entity_id:
            return []
        
        entity = self.entities[entity_id]
        timeline = []
        
        for mention in sorted(entity.mentions, key=lambda m: m.timestamp):
            timeline.append({
                "timestamp": mention.timestamp,
                "source": mention.source_url,
                "context": mention.context,
                "confidence": mention.confidence
            })
        
        return timeline
    
    def find_related_entities(self, entity_name: str, relationship_type: str = None) -> List[Dict[str, Any]]:
        """Find entities related to the given entity."""
        entity_id = self._find_entity_by_name(entity_name)
        if not entity_id:
            return []
        
        related = []
        for (e1_id, e2_id), rel_info in self.relationships.items():
            if relationship_type and rel_info["type"] != relationship_type:
                continue
                
            if e1_id == entity_id:
                related_entity = self.entities[e2_id]
                related.append({
                    "entity": related_entity,
                    "relationship": rel_info["type"],
                    "confidence": rel_info["confidence"]
                })
            elif e2_id == entity_id:
                related_entity = self.entities[e1_id]
                related.append({
                    "entity": related_entity,
                    "relationship": rel_info["type"],
                    "confidence": rel_info["confidence"]
                })
        
        return sorted(related, key=lambda x: x["confidence"], reverse=True)
    
    def _find_entity_by_name(self, name: str) -> Optional[str]:
        """Find entity ID by name or alias."""
        normalized = self._normalize_name(name)
        entity_ids = self.entity_index.get(normalized, [])
        
        if entity_ids:
            return entity_ids[0]  # Return most confident match
        
        # Check aliases
        for entity_id, entity in self.entities.items():
            for alias in entity.aliases:
                if self._normalize_name(alias) == normalized:
                    return entity_id
        
        return None
    
    def get_entities_by_type(self, entity_type: str) -> List[ResearchEntity]:
        """Get all entities of a specific type."""
        return [entity for entity in self.entities.values() if entity.entity_type == entity_type]
    
    def get_entity_context(self, entity_name: str) -> str:
        """Get comprehensive context about an entity."""
        entity_id = self._find_entity_by_name(entity_name)
        if not entity_id:
            return f"No information found about {entity_name}"
        
        entity = self.entities[entity_id]
        context_parts = [f"Entity: {entity.name} (Type: {entity.entity_type})"]
        
        if entity.attributes:
            context_parts.append(f"Attributes: {entity.attributes}")
        
        if entity.aliases:
            context_parts.append(f"Also known as: {', '.join(entity.aliases)}")
        
        # Add recent mentions
        recent_mentions = sorted(entity.mentions, key=lambda m: m.timestamp, reverse=True)[:3]
        for mention in recent_mentions:
            context_parts.append(f"Mentioned in: {mention.context[:200]}...")
        
        return "\n".join(context_parts)

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
        self.extracted_entities = {} # Legacy property for backward compatibility
        
        # Enhanced entity tracking
        self.knowledge_graph = ResearchKnowledgeGraph()
        self.current_research_phase = None
        self.research_phases = []
        self.core_facts = {}  # Facts that persist across research phases
    
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
        This version uses a more robust deduplication logic.
        
        Args:
            entities (dict): Dictionary of entity types and values
        """
        for entity_type, values in entities.items():
            if entity_type not in self.extracted_entities:
                self.extracted_entities[entity_type] = []
            
            # Use a set for faster lookups of existing entities (case-insensitive)
            existing_set = {e.lower() for e in self.extracted_entities[entity_type]}
            
            for value in values:
                # Skip very short entities as they're often false positives
                if len(str(value)) < 3:
                    continue
                
                value_lower = str(value).lower()
                
                # Simple check for exact duplicates
                if value_lower in existing_set:
                    continue

                # Check if a more specific version of this entity already exists
                # e.g., if 'Stripe, Inc.' exists, don't add 'Stripe'.
                is_less_specific = any(value_lower in existing for existing in existing_set)
                if is_less_specific:
                    continue

                # Check if this new entity is a more specific version of an existing one
                # e.g., if 'Stripe' exists, replace it with 'Stripe, Inc.'.
                found_less_specific = False
                for i, existing in enumerate(self.extracted_entities[entity_type]):
                    if existing.lower() in value_lower:
                        self.extracted_entities[entity_type][i] = value # Replace with more specific
                        existing_set.remove(existing.lower()) # Update the set
                        existing_set.add(value_lower)
                        found_less_specific = True
                        break
                
                if not found_less_specific:
                    self.extracted_entities[entity_type].append(value)
                    existing_set.add(value_lower)

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
        This version uses more flexible parsing.
        
        Args:
            role_name (str): Role name to search for (e.g., "CEO", "founder")
            
        Returns:
            tuple: (person_name, organization_name) or (None, None) if not found
        """
        if "role" not in self.extracted_entities:
            return None, None
            
        role_name_lower = role_name.lower()
        
        for role in self.extracted_entities["role"]:
            if role_name_lower in role.lower():
                # Flexible parsing for "Role: Person @ Organization" or similar formats
                # This is more robust than rigid splitting.
                parts = [p.strip() for p in role.replace(":", "@").split("@")]
                
                if len(parts) == 3: # e.g., "CEO", "John Doe", "Acme"
                    # Assuming the format is Role, Person, Org
                    return parts[1], parts[2]
                elif len(parts) == 2: # e.g., "John Doe", "Acme" (role was matched in the if)
                    return parts[0], parts[1]
                else:
                    # If parsing fails, return the full role string as the person
                    # and let the agent figure it out.
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

    def get_results(self, step_description=None):
        """
        Get results from the current task.
        
        Args:
            step_description (str, optional): If provided, get the result for a specific step.
        
        Returns:
            dict or list: A single result dict or a list of all result dicts.
        """
        if step_description:
            return self.task_results.get(step_description)
            
        # Convert task_results dict to a list of dicts with step info
        results = []
        for step_desc, output in self.task_results.items():
            # Determine status based on the presence of an 'error' key
            status = "error" if isinstance(output, dict) and 'error' in output else "success"
            results.append({
                "step": step_desc,
                "status": status, 
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
    
    # Enhanced entity-centric methods
    def extract_and_store_entities(self, content: str, source_url: str, entity_types: List[str] = None) -> Dict[str, List[str]]:
        """Extract entities from content and store in knowledge graph."""
        if not entity_types:
            entity_types = ["person", "organization", "location", "date", "statement", "role"]
        
        extracted = {}
        
        # Simple regex-based extraction (can be enhanced with NER)
        patterns = {
            "person": r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b',
            "organization": r'\b[A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Organization|Institute|Foundation|Group)\b',
            "date": r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|[A-Z][a-z]+ \d{1,2},?\s\d{4})\b',
            "statement": r'"([^"]{20,200})"',
            "role": r'\b(?:CEO|COO|CTO|President|Director|Manager|Secretary|Chairman|Vice President|VP)\b'
        }
        
        for entity_type in entity_types:
            if entity_type in patterns:
                matches = re.findall(patterns[entity_type], content, re.IGNORECASE)
                if matches:
                    extracted[entity_type] = []
                    for match in matches:
                        if entity_type == "statement":
                            match = match.strip()
                        if len(match) > 2:  # Filter very short matches
                            # Store in knowledge graph
                            entity_id = self.knowledge_graph.add_entity_mention(
                                entity_name=match,
                                entity_type=entity_type,
                                source_url=source_url,
                                context=content[:500],  # First 500 chars for context
                                confidence=0.8
                            )
                            extracted[entity_type].append(match)
        
        # Update legacy extracted_entities for backward compatibility
        for entity_type, entities in extracted.items():
            if entity_type not in self.extracted_entities:
                self.extracted_entities[entity_type] = []
            for entity in entities:
                if entity not in self.extracted_entities[entity_type]:
                    self.extracted_entities[entity_type].append(entity)
        
        return extracted
    
    def find_entity_relationships(self, source_url: str):
        """Identify and store relationships between entities from the same source."""
        entities_in_source = self.knowledge_graph.source_entities.get(source_url, [])
        
        # Find co-occurring entities and create relationships
        for i, entity1_id in enumerate(entities_in_source):
            for entity2_id in entities_in_source[i+1:]:
                entity1 = self.knowledge_graph.entities[entity1_id]
                entity2 = self.knowledge_graph.entities[entity2_id]
                
                # Create contextual relationships
                if entity1.entity_type == "person" and entity2.entity_type == "organization":
                    self.knowledge_graph.link_entities(
                        entity1_id, entity2_id, "affiliated_with", source_url, confidence=0.6
                    )
                elif entity1.entity_type == "role" and entity2.entity_type == "organization":
                    self.knowledge_graph.link_entities(
                        entity1_id, entity2_id, "role_at", source_url, confidence=0.7
                    )
                elif entity1.entity_type == "statement" and entity2.entity_type == "person":
                    self.knowledge_graph.link_entities(
                        entity2_id, entity1_id, "made_statement", source_url, confidence=0.8
                    )
    
    def get_entity_context_for_phase(self, phase_objective: str) -> str:
        """Get relevant entity context for current research phase."""
        if not self.current_research_phase:
            return ""
        
        relevant_entities = []
        phase_keywords = phase_objective.lower().split()
        
        for entity in self.knowledge_graph.entities.values():
            # Check if entity is relevant to phase objective
            entity_text = f"{entity.name} {entity.entity_type} {' '.join(entity.attributes.keys())}".lower()
            if any(keyword in entity_text for keyword in phase_keywords):
                relevant_entities.append(entity)
        
        # Sort by confidence and recency
        relevant_entities.sort(key=lambda e: (e.confidence, len(e.mentions)), reverse=True)
        
        context_parts = []
        for entity in relevant_entities[:5]:  # Top 5 most relevant
            context_parts.append(self.knowledge_graph.get_entity_context(entity.name))
        
        return "\n\n".join(context_parts)
    
    def add_core_fact(self, fact_key: str, fact_value: Any, source_url: str, confidence: float = 1.0):
        """Add a core fact that persists across research phases."""
        self.core_facts[fact_key] = {
            "value": fact_value,
            "source": source_url,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_core_facts(self) -> Dict[str, Any]:
        """Get all core facts for context."""
        return {key: fact["value"] for key, fact in self.core_facts.items()}
    
    def start_research_phase(self, phase_description: str, objective: str, required_entities: List[str]):
        """Start a new research phase."""
        self.current_research_phase = {
            "description": phase_description,
            "objective": objective,
            "required_entities": required_entities,
            "discovered_entities": {},
            "phase_results": {},
            "start_time": datetime.now().isoformat(),
            "status": "active"
        }
        self.research_phases.append(self.current_research_phase)
    
    def complete_research_phase(self, findings: Dict[str, Any]):
        """Complete the current research phase."""
        if self.current_research_phase:
            self.current_research_phase["findings"] = findings
            self.current_research_phase["status"] = "completed"
            self.current_research_phase["end_time"] = datetime.now().isoformat()
            
            # Extract core facts from findings
            for key, value in findings.items():
                if value and key not in self.core_facts:
                    self.add_core_fact(key, value, "research_phase", confidence=0.9)
    
    def get_research_progress(self) -> Dict[str, Any]:
        """Get current research progress across all phases."""
        return {
            "current_phase": self.current_research_phase,
            "completed_phases": [p for p in self.research_phases if p["status"] == "completed"],
            "total_entities": len(self.knowledge_graph.entities),
            "core_facts": len(self.core_facts)
        }
