from datetime import datetime
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Entity:
    """Enhanced entity representation with context"""
    name: str
    entity_type: str
    confidence: float
    contexts: List[str]  # Where this entity was mentioned
    sources: List[str]   # URLs where found
    attributes: Dict[str, Any]  # Additional attributes (role, location, etc.)
    first_seen: str
    last_updated: str

@dataclass 
class EntityRelationship:
    """Represents relationship between two entities"""
    entity1: str
    entity2: str
    relationship_type: str  # "works_at", "acquired", "located_in", etc.
    confidence: float
    context: str  # The sentence/context where relationship was found
    source: str

class EntityGraph:
    """Strategic entity tracking and relationship management"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[EntityRelationship] = []
        self.entity_types = {
            'person', 'organization', 'role', 'location', 'temporal', 
            'financial', 'event', 'product', 'technology'
        }
    
    def add_entity(self, name: str, entity_type: str, context: str, source: str, 
                   confidence: float = 0.8, attributes: Dict = None) -> Entity:
        """Add or update an entity with context awareness"""
        
        # Normalize entity name
        normalized_name = self._normalize_entity_name(name)
        
        # Check if entity exists (fuzzy matching)
        existing_key = self._find_existing_entity(normalized_name, entity_type)
        
        if existing_key:
            # Update existing entity
            entity = self.entities[existing_key]
            entity.contexts.append(context)
            entity.sources.append(source)
            entity.confidence = max(entity.confidence, confidence)
            entity.last_updated = datetime.now().isoformat()
            if attributes:
                entity.attributes.update(attributes)
        else:
            # Create new entity
            entity = Entity(
                name=normalized_name,
                entity_type=entity_type,
                confidence=confidence,
                contexts=[context],
                sources=[source],
                attributes=attributes or {},
                first_seen=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            )
            self.entities[self._entity_key(normalized_name, entity_type)] = entity
        
        return entity
    
    def add_relationship(self, entity1: str, entity2: str, relationship_type: str,
                        context: str, source: str, confidence: float = 0.7):
        """Add relationship between entities"""
        
        # Normalize entity names
        entity1 = self._normalize_entity_name(entity1)  
        entity2 = self._normalize_entity_name(entity2)
        
        # Check if relationship already exists
        existing = self._find_existing_relationship(entity1, entity2, relationship_type)
        if not existing:
            relationship = EntityRelationship(
                entity1=entity1,
                entity2=entity2, 
                relationship_type=relationship_type,
                confidence=confidence,
                context=context,
                source=source
            )
            self.relationships.append(relationship)
    
    def get_entity_by_role(self, role: str, organization: str = None) -> Optional[Entity]:
        """Find person entity with specific role, optionally at specific organization"""
        role_lower = role.lower()
        
        for entity in self.entities.values():
            if entity.entity_type == 'person':
                # Check attributes for role
                if 'role' in entity.attributes and role_lower in entity.attributes['role'].lower():
                    if organization:
                        # Check if person is related to the organization
                        if self._entities_related(entity.name, organization):
                            return entity
                    else:
                        return entity
        
        return None
    
    def get_organization_from_event(self, event_keywords: List[str]) -> Optional[Entity]:
        """Find organization mentioned in context of specific event"""
        for entity in self.entities.values():
            if entity.entity_type == 'organization':
                for context in entity.contexts:
                    context_lower = context.lower()
                    if any(keyword.lower() in context_lower for keyword in event_keywords):
                        return entity
        return None
    
    def get_connected_entities(self, entity_name: str, relationship_types: List[str] = None) -> List[Entity]:
        """Get entities connected to given entity through relationships"""
        connected = []
        entity_name_norm = self._normalize_entity_name(entity_name)
        
        for rel in self.relationships:
            if relationship_types and rel.relationship_type not in relationship_types:
                continue
                
            connected_name = None
            if rel.entity1 == entity_name_norm:
                connected_name = rel.