from typing import List, Dict, Any
import re
from .base import Strategy, StrategyResult

class CodingStrategy(Strategy):
    def __init__(self):
        self.coding_keywords = [
            "implement", "code", "write", "create", "develop",
            "function", "class", "algorithm", "program",
            "generate", "build"
        ]
        self.language_patterns = {
            "python": r"python|django|flask",
            "javascript": r"javascript|react|node|js",
            "typescript": r"typescript|angular|ts",
            "go": r"golang|go lang|go program"
        }

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        keyword_matches = sum(1 for kw in self.coding_keywords if kw in task_lower)
        has_language = any(re.search(pattern, task_lower) 
                         for pattern in self.language_patterns.values())
        return min((keyword_matches * 0.2) + (0.3 if has_language else 0), 1.0)

    def get_required_tools(self) -> List[str]:
        return ["code_analysis", "google_search"]

    def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        steps = []
        
        # Step 1: Research similar implementations
        steps.append({
            "tool": "google_search",
            "input": f"github {task} example implementation",
            "purpose": "reference_search"
        })
        
        # Step 2: Analyze similar code
        steps.append({
            "tool": "code_analysis",
            "input": {
                "command": "analyze",
                "code": "{previous_result}"
            },
            "purpose": "pattern_analysis"
        })
        
        # Step 3: Generate implementation
        steps.append({
            "tool": "code_analysis",
            "input": {
                "command": "generate",
                "context": task
            },
            "purpose": "implementation"
        })
        
        # Step 4: Security check
        steps.append({
            "tool": "code_analysis",
            "input": {
                "command": "security_check",
                "code": "{generated_code}"
            },
            "purpose": "security_verification"
        })
        
        return StrategyResult(
            success=True,
            steps_taken=steps,
            output="Coding steps defined",
            confidence=0.9,
            metadata={
                "strategy_type": "coding",
                "requires_security_check": True
            }
        )
