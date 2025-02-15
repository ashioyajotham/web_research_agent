from models.llm import LLMInterface
from typing import List, Dict, Any
from utils.helpers import logger

class Comprehension:
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self.knowledge_base = []

    def process_task(self, task):
        processed_info = self._understand_task(task)
        self.knowledge_base.append(processed_info)

    async def synthesize_results(self, results: List[str]) -> str:
        """Synthesize multiple results into a coherent response"""
        try:
            results_text = '\n'.join(results)
            prompt = f"""Synthesize these research results into a clear, coherent response:
{results_text}

Provide a well-structured summary that:
1. Highlights key findings
2. Connects related information
3. Resolves any contradictions"""
            return await self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"Failed to synthesize results: {str(e)}")
            return "Error synthesizing results"

    async def _understand_task(self, task: str) -> Dict[str, Any]:
        """Analyze and understand the given task"""
        try:
            prompt = f"""Analyze this task and extract:
1. Main objective
2. Key requirements
3. Potential challenges

Task: {task}
Return as JSON."""
            return await self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"Task understanding failed: {str(e)}")
            raise

    def adapt_to_future_tasks(self, new_task):
        # Logic to adapt based on previous tasks
        return f"Adapting to new task: {new_task}"