from utils.logger import get_logger

logger = get_logger(__name__)

class Comprehension:
    """Text understanding and reasoning capabilities."""
    
    def __init__(self):
        """Initialize the comprehension module."""
        self.model = None
        self.last_strategy = None
    
    def analyze_task(self, task_description):
        """
        Analyze a task to determine its type, required information, etc.
        """
        logger.info(f"Analyzing task: {task_description}")

        # Task-agnostic, pattern-only routing for list-of-statements/quotes
        tl = (task_description or "").lower()
        is_list_intent = any(w in tl for w in ["compile", "list", "gather", "collect"])
        targets_statements = any(w in tl for w in ["statement", "statements", "quote", "quotes", "remark", "remarks", "said", "says"])
        if is_list_intent and targets_statements:
            analysis = {
                "task_type": "information_gathering",
                "answer_type": "list_compilation",
                "information_targets": ["statements", "quotes", "remarks"],
                "synthesis_strategy": "collect_and_organize",
                "presentation_format": "list",
            }
            self.last_strategy = "collect_and_organize"
            return analysis

        # Fallback (keep generic)
        analysis = {
            "task_type": "general_research",
            "synthesis_strategy": "comprehensive_synthesis",
            "presentation_format": "summary",
        }
        self.last_strategy = "comprehensive_synthesis"
        return analysis
