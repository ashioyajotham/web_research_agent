from typing import List, Dict, Any
import re
from .base import Strategy, StrategyResult
from datetime import datetime
from dateutil import parser

class ResearchStrategy(Strategy):
    def __init__(self):
        self.research_keywords = [
            "find", "search", "analyze", "compare", "list",
            "what", "when", "where", "who", "how",
            "summarize", "explain", "describe"
        ]
        self.timeline_patterns = [
            r'(?P<date>\w+\s+\d{1,2},?\s+\d{4})\s*[:-]\s*(?P<event>.*?)(?=\w+\s+\d{1,2},?\s+\d{4}|\Z)',
            r'(?:in|on|during)\s+(?P<date>\w+\s+\d{4})[,:\s]+(?P<event>.*?)(?=(?:in|on|during)\s+\w+\s+\d{4}|\Z)',
            r'(?P<date>\d{4})\s*:\s*(?P<event>.*?)(?=\d{4}:|\Z)'
        ]
        
        # Add credibility scoring
        self.source_credibility = {
            'academic': ['edu', 'ac.', 'research', 'journal'],
            'official': ['gov', 'org', 'ieee', 'iso'],
            'industry': ['tech', 'dev', 'engineering', 'official'],
            'news': ['news', 'times', 'post', 'tribune']
        }
        
        # Add topic categorization
        self.topic_categories = {
            'technical': ['implementation', 'architecture', 'protocol', 'algorithm'],
            'research': ['study', 'research', 'discovery', 'breakthrough'],
            'business': ['market', 'industry', 'adoption', 'commercial'],
            'impact': ['effect', 'influence', 'change', 'revolution']
        }

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        keyword_matches = sum(1 for kw in self.research_keywords if kw in task_lower)
        return min(keyword_matches * 0.2, 1.0)

    def get_required_tools(self) -> List[str]:
        return ["google_search", "web_scraper"]

    async def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        try:
            if not context or 'tools' not in context:
                return StrategyResult(success=False, error="Missing required tools in context")

            # Step 1: Initial broad search
            search_results = await context['tools']['google_search'].execute(task)
            if not search_results or not search_results.get('success'):
                return StrategyResult(success=False, error="Search failed")
            
            # Step 2: Extract and validate findings
            events = self._extract_chronological_events(search_results)
            if not events:
                return StrategyResult(
                    success=True,
                    output={
                        "summary": "No relevant timeline events found",
                        "timeline": {},
                        "major_milestones": [],
                        "latest_developments": [],
                        "sources": []
                    },
                    confidence=0.5
                )
            
            # Step 3: Source credibility analysis
            credibility_scores = self._analyze_source_credibility(events)
            
            # Step 4: Topic categorization
            categorized_findings = self._categorize_findings(events)
            
            # Step 5: Cross-reference and validate
            validated_events = self._cross_reference_findings(events)
            
            # Step 6: Generate synthesis
            synthesis = self._generate_research_synthesis(
                validated_events, 
                categorized_findings,
                credibility_scores
            )
            
            output = {
                "summary": synthesis['overview'],
                "timeline": self._group_events(validated_events),
                "major_milestones": self._extract_major_milestones(validated_events),
                "latest_developments": synthesis['latest'],
                "key_findings": synthesis['key_points'],
                "categories": categorized_findings,
                "credibility": {
                    'overall_score': sum(credibility_scores.values()) / len(credibility_scores),
                    'source_scores': credibility_scores
                },
                "sources": self._format_sources(validated_events)
            }

            return StrategyResult(
                success=True,
                output=output,
                confidence=synthesis['confidence'],
                metadata={
                    'categories': list(categorized_findings.keys()),
                    'timeline_range': f"{validated_events[0]['date']} - {validated_events[-1]['date']}"
                    if validated_events else None
                }
            )

        except Exception as e:
            return StrategyResult(success=False, error=str(e))

    def _extract_chronological_events(self, search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract dated events from search results with better error handling"""
        try:
            events = []
            results = search_results.get('results', [])
            
            if not results:
                return []

            for result in results:
                snippet = result.get('snippet', '')
                title = result.get('title', '')
                date = result.get('date', '')
                url = result.get('link', '')
                
                # Extract dates and associated events
                date_event_pairs = []
                
                # Try explicit date from result
                if date:
                    date_event_pairs.append((date, snippet))
                
                # Extract dates from content
                for pattern in self.timeline_patterns:
                    matches = re.finditer(pattern, snippet)
                    for match in matches:
                        date_str = match.group('date')
                        event_text = match.group('event').strip()
                        if date_str and event_text:
                            date_event_pairs.append((date_str, event_text))
                
                # Add events with dates
                for date_str, event_text in date_event_pairs:
                    try:
                        parsed_date = self._parse_date(date_str)
                        if parsed_date != datetime.min:  # Valid date
                            events.append({
                                'date': date_str,
                                'event': event_text,
                                'source': title,
                                'url': url,
                                'parsed_date': parsed_date  # For sorting
                            })
                    except Exception:
                        continue
            
            # Sort by date
            return sorted(events, key=lambda x: x.get('parsed_date', datetime.min))
            
        except Exception:
            return []

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats with better handling"""
        try:
            # Add more date format patterns if needed
            date_patterns = [
                r'(\d{4})',  # Year only
                r'([A-Za-z]+\s+\d{4})',  # Month Year
                r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})',  # Month Day, Year
            ]
            
            # Try direct parsing first
            try:
                return parser.parse(date_str, fuzzy=True)
            except:
                pass
            
            # Try patterns
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    try:
                        return parser.parse(match.group(1), fuzzy=True)
                    except:
                        continue
                        
            return datetime.min
            
        except Exception:
            return datetime.min

    def _group_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Group events by year and quarter with datetime handling"""
        grouped = {}
        for event in events:
            # Convert datetime to string in the event dict
            if 'parsed_date' in event and isinstance(event['parsed_date'], datetime):
                event['parsed_date'] = event['parsed_date'].isoformat()
            
            date = self._parse_date(event['date'])
            year = str(date.year)
            quarter = f"Q{(date.month-1)//3 + 1}"
            
            if year not in grouped:
                grouped[year] = {}
            if quarter not in grouped[year]:
                grouped[year][quarter] = []
                
            grouped[year][quarter].append(event)
            
        return grouped

    def _extract_major_milestones(self, events: List[Dict]) -> List[Dict]:
        """Extract major milestones using keyword analysis"""
        milestone_keywords = [
            'breakthrough', 'milestone', 'achievement', 'major', 'significant',
            'revolutionary', 'pioneering', 'first', 'novel', 'unprecedented'
        ]
        
        return [
            event for event in events
            if any(keyword in event['event'].lower() for keyword in milestone_keywords)
        ]

    def _analyze_source_credibility(self, events: List[Dict]) -> Dict[str, float]:
        """Analyze source credibility based on domain and citations"""
        scores = {}
        for event in events:
            url = event.get('url', '')
            source = event.get('source', '')
            
            # Base score
            score = 0.5
            
            # Domain type bonus
            for category, keywords in self.source_credibility.items():
                if any(kw in url.lower() for kw in keywords):
                    score += 0.1
                    break
                    
            # Citation and reference bonus
            if any(ref in source.lower() for ref in ['cited', 'reference', 'according']):
                score += 0.1
                
            scores[source] = min(score, 1.0)
            
        return scores

    def _categorize_findings(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize findings by topic and relevance"""
        categories = {cat: [] for cat in self.topic_categories.keys()}
        
        for event in events:
            event_text = f"{event.get('event', '')} {event.get('source', '')}"
            
            for category, keywords in self.topic_categories.items():
                if any(kw in event_text.lower() for kw in keywords):
                    categories[category].append(event)
                    
        return categories

    def _cross_reference_findings(self, events: List[Dict]) -> List[Dict]:
        """Validate findings through cross-referencing"""
        validated = []
        event_map = {}
        
        # Group similar events
        for event in events:
            key = self._generate_event_key(event['event'])
            if key not in event_map:
                event_map[key] = []
            event_map[key].append(event)
        
        # Validate events with multiple sources
        for similar_events in event_map.values():
            if len(similar_events) > 1:  # Multiple sources confirm
                best_event = max(similar_events, 
                               key=lambda x: len(x.get('source', '')))
                best_event['confirmation_count'] = len(similar_events)
                validated.append(best_event)
            else:  # Single source - lower confidence
                event = similar_events[0]
                event['confirmation_count'] = 1
                validated.append(event)
                
        return sorted(validated, key=lambda x: self._parse_date(x['date']))

    def _generate_research_synthesis(self, events: List[Dict], categories: Dict[str, List[Dict]], credibility: Dict[str, float]) -> Dict[str, Any]:
        """Generate comprehensive research synthesis"""
        try:
            if not events:
                return {
                    'overview': "No relevant research findings available",
                    'latest': [],
                    'key_points': [],
                    'confidence': 0.5
                }
            
            # Sort events by date for latest developments
            sorted_events = sorted(events, key=lambda x: x.get('parsed_date', datetime.min), reverse=True)
            latest_events = sorted_events[:5]  # Get 5 most recent events
            
            # Generate key points from categorized findings
            key_points = []
            for category, cat_events in categories.items():
                if cat_events:
                    # Get the most significant event for each category
                    significant_event = max(cat_events, 
                                         key=lambda x: x.get('confirmation_count', 1))
                    key_points.append({
                        'category': category,
                        'point': significant_event['event']
                    })
            
            # Calculate overall confidence based on source credibility
            avg_credibility = sum(credibility.values()) / len(credibility) if credibility else 0.5
            confidence = min(0.9, avg_credibility + 0.1 * len(key_points))
            
            return {
                'overview': self._generate_overview(events, categories),
                'latest': latest_events,
                'key_points': key_points,
                'confidence': confidence
            }
            
        except Exception as e:
            return {
                'overview': "Error generating research synthesis",
                'latest': [],
                'key_points': [],
                'confidence': 0.0
            }

    def _generate_overview(self, events: List[Dict], categories: Dict[str, List[Dict]]) -> str:
        """Generate a concise overview of the research findings"""
        try:
            if not events:
                return "No significant findings to report."
            
            # Get date range
            dates = [e.get('parsed_date') for e in events if e.get('parsed_date')]
            if dates:
                date_range = f"From {min(dates).year} to {max(dates).year}"
            else:
                date_range = "Recent period"
            
            # Count significant developments by category
            category_counts = {cat: len(events) for cat, events in categories.items() if events}
            main_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            overview = f"{date_range}, research shows significant developments in "
            overview += ", ".join(cat for cat, _ in main_categories) if main_categories else "various areas"
            
            return overview
            
        except Exception:
            return "Research findings overview not available."

    def _format_sources(self, events: List[Dict]) -> List[Dict]:
        """Format source information from events with proper datetime handling"""
        try:
            if not events:
                return []
            
            # Deduplicate sources while preserving order
            seen_sources = set()
            unique_sources = []
            
            for event in events:
                source_key = (event.get('source', ''), event.get('url', ''))
                if source_key not in seen_sources and event.get('source'):
                    seen_sources.add(source_key)
                    
                    # Convert datetime to string if present
                    date = event.get('date', '')
                    if isinstance(date, datetime):
                        date = date.isoformat()
                    
                    unique_sources.append({
                        'title': event['source'],
                        'url': event.get('url', ''),
                        'date': date
                    })
            
            return unique_sources
            
        except Exception:
            return []

    def _generate_event_key(self, event_text: str) -> str:
        """Generate a normalized key for event comparison"""
        # Remove common filler words and normalize text
        filler_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        normalized = ' '.join(
            word.lower() for word in event_text.split() 
            if word.lower() not in filler_words
        )
        
        # Extract key phrases based on patterns
        key_patterns = [
            r'(?:announced|launched|released|introduced|developed)\s+([^.]+)',
            r'(?:breakthrough|achievement|milestone)\s+in\s+([^.]+)',
            r'(?:first|new|novel)\s+([^.]+)',
        ]
        
        for pattern in key_patterns:
            match = re.search(pattern, normalized)
            if match:
                return match.group(1).strip()
        
        # Fallback: use first N significant words
        words = normalized.split()
        return ' '.join(words[:5]) if words else normalized

    def _handle_person_query(self, snippet: str) -> Dict[str, Any]:
        """Specialized handler for person-related queries"""
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\(([^)]+)\))?',  # Name with optional title
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,\s*([^,]+)'  # Name with description
        ]
        
        for pattern in re.finditer(patterns[0], snippet):
            name, title = pattern.groups()
            if title:
                return {'name': name.strip(), 'title': title.strip()}
        
        for pattern in re.finditer(patterns[1], snippet):
            name, desc = pattern.groups()
            return {'name': name.strip(), 'description': desc.strip()}
            
        return None

    def _extract_direct_answer(self, query: str, results: List[Dict[str, str]]) -> str:
        """Extract clean direct answers without source prefixes"""
        query_lower = query.lower()
        
        # Handle "who is richest" type queries
        if any(term in query_lower for term in ['richest', 'wealthiest']):
            for result in results:
                snippet = result.get('snippet', '')
                matches = re.search(
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:is|remains|became)\s+(?:the\s+)?(?:world\'?s?\s+)?richest',
                    snippet
                )
                if matches:
                    person_info = self._handle_person_query(snippet)
                    if person_info:
                        return f"{person_info['name']} ({person_info.get('title', person_info.get('description', ''))})"
                    return matches.group(1).strip()
        
        return None
