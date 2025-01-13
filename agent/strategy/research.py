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
            # Step 1: Initial broad search
            search_results = await context['tools']['google_search'].execute(task)
            
            # Step 2: Extract and validate findings
            events = self._extract_chronological_events(search_results)
            
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

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        try:
            return parser.parse(date_str, fuzzy=True)
        except:
            return datetime.min

    def _group_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Group events by year and quarter"""
        grouped = {}
        for event in events:
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

    def _generate_research_synthesis(self, 
                                  events: List[Dict],
                                  categories: Dict[str, List[Dict]],
                                  credibility: Dict[str, float]) -> Dict[str, Any]:
        """Generate comprehensive research synthesis"""
        # ...implementation of synthesis generation...
