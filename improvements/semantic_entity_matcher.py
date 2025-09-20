import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import difflib

@dataclass
class EntityMatch:
    """Represents a match between entities."""
    entity1_id: str
    entity2_id: str
    similarity_score: float
    match_type: str  # "exact", "fuzzy", "semantic", "acronym", "alias"
    confidence: float

class SemanticEntityMatcher:
    """Advanced entity matching using multiple similarity techniques."""
    
    def __init__(self):
        # Common organization name variations
        self.org_normalizations = {
            'inc': 'incorporated',
            'corp': 'corporation', 
            'llc': 'limited liability company',
            'ltd': 'limited',
            'co': 'company',
            '&': 'and',
            'intl': 'international',
            'natl': 'national',
            'assn': 'association',
            'inst': 'institute'
        }
        
        # Common person name patterns
        self.name_patterns = {
            'jr': 'junior',
            'sr': 'senior',
            'ii': 'second',
            'iii': 'third',
            'iv': 'fourth'
        }
        
        # Role synonyms
        self.role_synonyms = {
            'ceo': ['chief executive officer', 'chief exec', 'president and ceo'],
            'coo': ['chief operating officer', 'chief operations officer', 'president and coo'],
            'cto': ['chief technology officer', 'chief technical officer'],
            'cfo': ['chief financial officer'],
            'president': ['pres', 'chairman and president'],
            'chairman': ['chair', 'chairperson', 'board chair'],
            'director': ['dir', 'managing director', 'executive director']
        }
        
        # Cache for expensive computations
        self._similarity_cache = {}
    
    def find_similar_entities(self, target_entity: str, entity_type: str, 
                            existing_entities: List[Dict[str, Any]], 
                            threshold: float = 0.7) -> List[EntityMatch]:
        """Find similar entities using multiple matching techniques."""
        matches = []
        
        for existing in existing_entities:
            if existing.get('entity_type') != entity_type:
                continue
                
            existing_name = existing.get('name', '')
            existing_id = existing.get('id', '')
            
            # Skip empty names
            if not existing_name or not target_entity:
                continue
                
            # Try different matching approaches
            match_results = [
                self._exact_match(target_entity, existing_name),
                self._fuzzy_match(target_entity, existing_name),
                self._normalized_match(target_entity, existing_name, entity_type),
                self._acronym_match(target_entity, existing_name),
                self._partial_match(target_entity, existing_name),
                self._semantic_role_match(target_entity, existing_name, entity_type)
            ]
            
            # Find the best match
            best_match = max(match_results, key=lambda x: x[0] if x else 0)
            
            if best_match and best_match[0] >= threshold:
                similarity_score, match_type = best_match
                
                # Calculate confidence based on match type and score
                confidence = self._calculate_match_confidence(similarity_score, match_type, 
                                                           target_entity, existing_name)
                
                match = EntityMatch(
                    entity1_id=f"target_{hashlib.md5(target_entity.encode()).hexdigest()[:8]}",
                    entity2_id=existing_id,
                    similarity_score=similarity_score,
                    match_type=match_type,
                    confidence=confidence
                )
                matches.append(match)
        
        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches
    
    def _exact_match(self, name1: str, name2: str) -> Optional[Tuple[float, str]]:
        """Check for exact string match."""
        if name1.lower().strip() == name2.lower().strip():
            return (1.0, "exact")
        return None
    
    def _fuzzy_match(self, name1: str, name2: str) -> Optional[Tuple[float, str]]:
        """Use fuzzy string matching."""
        similarity = difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        
        if similarity >= 0.8:
            return (similarity, "fuzzy")
        return None
    
    def _normalized_match(self, name1: str, name2: str, entity_type: str) -> Optional[Tuple[float, str]]:
        """Match after normalizing common variations."""
        norm1 = self._normalize_entity_name(name1, entity_type)
        norm2 = self._normalize_entity_name(name2, entity_type)
        
        if norm1 == norm2:
            return (0.95, "normalized")
        
        # Check similarity of normalized versions
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        if similarity >= 0.9:
            return (similarity * 0.9, "normalized")  # Slight penalty for normalization
        
        return None
    
    def _acronym_match(self, name1: str, name2: str) -> Optional[Tuple[float, str]]:
        """Check if one name is an acronym of the other."""
        acronym1 = self._extract_acronym(name1)
        acronym2 = self._extract_acronym(name2)
        
        # Check if either is an acronym of the other
        if acronym1 and (acronym1.lower() == name2.lower().replace(' ', '')):
            return (0.85, "acronym")
        
        if acronym2 and (acronym2.lower() == name1.lower().replace(' ', '')):
            return (0.85, "acronym")
        
        # Check common acronyms
        if acronym1 and acronym2 and acronym1.lower() == acronym2.lower():
            return (0.9, "acronym")
        
        return None
    
    def _partial_match(self, name1: str, name2: str) -> Optional[Tuple[float, str]]:
        """Check for partial matches (one name contained in another)."""
        name1_clean = re.sub(r'[^\w\s]', '', name1.lower()).strip()
        name2_clean = re.sub(r'[^\w\s]', '', name2.lower()).strip()
        
        # Skip very short names to avoid false positives
        if len(name1_clean) < 4 or len(name2_clean) < 4:
            return None
        
        # Check if one is contained in the other
        if name1_clean in name2_clean or name2_clean in name1_clean:
            # Calculate containment ratio
            shorter = min(len(name1_clean), len(name2_clean))
            longer = max(len(name1_clean), len(name2_clean))
            ratio = shorter / longer
            
            if ratio >= 0.6:  # At least 60% containment
                return (ratio * 0.8, "partial")  # Penalty for partial match
        
        return None
    
    def _semantic_role_match(self, name1: str, name2: str, entity_type: str) -> Optional[Tuple[float, str]]:
        """Match based on semantic understanding of roles."""
        if entity_type != "role":
            return None
        
        role1_normalized = self._normalize_role(name1)
        role2_normalized = self._normalize_role(name2)
        
        if role1_normalized == role2_normalized:
            return (0.95, "semantic")
        
        # Check role synonyms
        for canonical_role, synonyms in self.role_synonyms.items():
            if (role1_normalized == canonical_role and any(syn in name2.lower() for syn in synonyms)) or \
               (role2_normalized == canonical_role and any(syn in name1.lower() for syn in synonyms)):
                return (0.85, "semantic")
        
        return None
    
    def _normalize_entity_name(self, name: str, entity_type: str) -> str:
        """Normalize entity name for comparison."""
        # Basic cleanup
        normalized = re.sub(r'[^\w\s&]', '', name.lower()).strip()
        
        # Entity-specific normalizations
        if entity_type == "organization":
            # Apply organization normalizations
            words = normalized.split()
            normalized_words = []
            
            for word in words:
                if word in self.org_normalizations:
                    normalized_words.append(self.org_normalizations[word])
                else:
                    normalized_words.append(word)
            
            normalized = ' '.join(normalized_words)
            
            # Remove common suffixes for comparison
            suffixes = ['incorporated', 'corporation', 'company', 'limited', 'llc', 'inc', 'corp', 'ltd']
            for suffix in suffixes:
                if normalized.endswith(' ' + suffix):
                    normalized = normalized[:-len(suffix)-1]
                    break
        
        elif entity_type == "person":
            # Apply person name normalizations
            words = normalized.split()
            normalized_words = []
            
            for word in words:
                if word in self.name_patterns:
                    normalized_words.append(self.name_patterns[word])
                else:
                    normalized_words.append(word)
            
            normalized = ' '.join(normalized_words)
        
        return normalized.strip()
    
    def _normalize_role(self, role: str) -> str:
        """Normalize role titles."""
        role_lower = role.lower().strip()
        
        # Remove common prefixes/suffixes
        role_lower = re.sub(r'^(the\s+)?', '', role_lower)
        role_lower = re.sub(r'\s+(of\s+.+)$', '', role_lower)
        
        # Map to canonical forms
        for canonical, synonyms in self.role_synonyms.items():
            if role_lower == canonical:
                return canonical
            if any(syn in role_lower for syn in synonyms):
                return canonical
        
        return role_lower
    
    def _extract_acronym(self, text: str) -> Optional[str]:
        """Extract potential acronym from text."""
        words = re.findall(r'\b[A-Z][a-z]*\b', text)
        if len(words) >= 2:
            return ''.join(word[0] for word in words)
        
        # Check if text is already an acronym
        if re.match(r'^[A-Z]{2,6}$', text.strip()):
            return text.strip()
        
        return None
    
    def _calculate_match_confidence(self, similarity_score: float, match_type: str, 
                                  name1: str, name2: str) -> float:
        """Calculate confidence in the match."""
        base_confidence = similarity_score
        
        # Adjust based on match type
        type_multipliers = {
            "exact": 1.0,
            "fuzzy": 0.9,
            "normalized": 0.85,
            "acronym": 0.8,
            "partial": 0.7,
            "semantic": 0.9
        }
        
        confidence = base_confidence * type_multipliers.get(match_type, 0.5)
        
        # Adjust based on name characteristics
        name1_len = len(name1.strip())
        name2_len = len(name2.strip())
        
        # Penalty for very short names (more likely false positives)
        if min(name1_len, name2_len) < 5:
            confidence *= 0.8
        
        # Bonus for longer, more specific names
        if min(name1_len, name2_len) > 20:
            confidence *= 1.1
        
        # Penalty for large length differences
        length_ratio = min(name1_len, name2_len) / max(name1_len, name2_len)
        if length_ratio < 0.5:
            confidence *= 0.7
        
        return min(confidence, 1.0)
    
    def deduplicate_entities(self, entities: List[Dict[str, Any]], 
                           similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Remove duplicate entities from a list."""
        if not entities:
            return entities
        
        # Group entities by type
        entities_by_type = defaultdict(list)
        for entity in entities:
            entity_type = entity.get('entity_type', 'unknown')
            entities_by_type[entity_type].append(entity)
        
        deduplicated = []
        
        for entity_type, entity_list in entities_by_type.items():
            if len(entity_list) <= 1:
                deduplicated.extend(entity_list)
                continue
            
            # Find duplicates within this type
            kept_entities = []
            skip_indices = set()
            
            for i, entity in enumerate(entity_list):
                if i in skip_indices:
                    continue
                
                entity_name = entity.get('name', '')
                similar_matches = self.find_similar_entities(
                    entity_name, entity_type, entity_list[i+1:], similarity_threshold
                )
                
                if similar_matches:
                    # This entity has duplicates, merge them
                    merged_entity = self._merge_entities([entity] + [
                        entity_list[j] for j, other in enumerate(entity_list[i+1:], i+1)
                        if any(match.entity2_id == other.get('id') for match in similar_matches)
                    ])
                    kept_entities.append(merged_entity)
                    
                    # Skip the merged entities
                    for j, other in enumerate(entity_list[i+1:], i+1):
                        if any(match.entity2_id == other.get('id') for match in similar_matches):
                            skip_indices.add(j)
                else:
                    # No duplicates found, keep as is
                    kept_entities.append(entity)
            
            deduplicated.extend(kept_entities)
        
        return deduplicated
    
    def _merge_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple similar entities into one."""
        if len(entities) == 1:
            return entities[0]
        
        # Use the entity with the highest confidence as base
        base_entity = max(entities, key=lambda e: e.get('confidence', 0))
        merged = base_entity.copy()
        
        # Merge sources
        all_sources = set()
        for entity in entities:
            sources = entity.get('sources', [])
            if isinstance(sources, list):
                all_sources.update(sources)
            elif isinstance(sources, str):
                all_sources.add(sources)
        
        merged['sources'] = list(all_sources)
        
        # Merge contexts
        all_contexts = []
        for entity in entities: