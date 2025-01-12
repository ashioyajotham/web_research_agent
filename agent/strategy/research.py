from typing import List, Dict, Any
import re
from .base import Strategy, StrategyResult

class ResearchStrategy(Strategy):
    def __init__(self):
        self.research_keywords = [
            "find", "search", "analyze", "compare", "list",
            "what", "when", "where", "who", "how",
            "summarize", "explain", "describe"
        ]

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        keyword_matches = sum(1 for kw in self.research_keywords if kw in task_lower)
        return min(keyword_matches * 0.2, 1.0)

    def get_required_tools(self) -> List[str]:
        return ["google_search", "web_scraper"]

    def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        steps = []
        
        # Step 1: Initial broad search
        steps.append({
            "tool": "google_search",
            "input": task,
            "purpose": "initial_research"
        })
        
        # Step 2: Focused information gathering
        steps.append({
            "tool": "web_scraper",
            "input": "{previous_urls}",
            "purpose": "detailed_info"
        })
        
        # Step 3: Verification search
        steps.append({
            "tool": "google_search",
            "input": f"verify {task}",
            "purpose": "fact_checking"
        })
        
        return StrategyResult(
            success=True,
            steps_taken=steps,
            output="Research steps defined",
            confidence=0.8,
            metadata={
                "strategy_type": "research",
                "verification_needed": True
            }
        )
