from models.llm import LLMInterface
from typing import List, Dict, Any
from utils.helpers import logger
import json
import re

class Comprehension:
    def __init__(self, llm):
        self.llm = llm
        self.knowledge_base = []

    def process_task(self, task):
        processed_info = self._understand_task(task)
        self.knowledge_base.append(processed_info)

    async def synthesize_results(self, results: List[str]) -> str:
        """Synthesize multiple results into a coherent response"""
        try:
            # Get task context from knowledge base
            task_context = self.knowledge_base[-1] if self.knowledge_base else {}
            
            # Join results with proper line breaks
            research_data = "\n".join(str(result) for result in results)
            
            prompt = f"""Synthesize these research results into a comprehensive response:

Research Data:
{research_data}

Task Context:
{json.dumps(task_context, indent=2)}

Synthesis Requirements:
1. Format output in clear Markdown with appropriate headers
2. Provide specific sources for factual claims or quotes
3. Adapt structure based on content type (data, statements, analysis, etc.)
4. Include relevant context (dates, locations, organizations)
5. Highlight key uncertainties or data gaps
6. Add a "Methodology" section explaining how conclusions were reached
7. End with a "Sources" section listing references with quality indicators"""

            response = await self.llm.generate(prompt)
            return response

        except Exception as e:
            logger.error(f"Failed to synthesize results: {str(e)}")
            return "Error synthesizing results"

    def _extract_sources(self, results: List[str]) -> List[str]:
        """Extract source information from results"""
        sources = set()
        url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        
        for result in results:
            if isinstance(result, dict) and 'source' in result:
                sources.add(result['source'])
            elif isinstance(result, str):
                urls = url_pattern.findall(result)
                sources.update(urls)
        
        return list(sources) or ["No specific sources identified"]

    async def _understand_task(self, task: str) -> Dict[str, Any]:
        """Analyze and understand the task structure and requirements"""
        try:
            prompt = f"""Analyze this task and extract its structure:

Task: {task}

Return a JSON object with this structure:
{{
    "type": "simple" | "multi_criteria" | "comparative" | "time_series" | "data_analysis",
    "components": ["subtask1", "subtask2"],
    "dependencies": {{"subtask2": ["subtask1"]}},
    "requirements": {{"data_needed": [], "source_types": []}},
    "validation_needs": [],
    "temporal_aspect": "none" | "historical" | "current" | "future",
    "output_format": "list" | "analysis" | "comparison" | "timeline"
}}"""

            response = await self.llm.generate(prompt)
            
            # Clean up response
            cleaned_json = response.strip()
            if cleaned_json.startswith('```json'):
                cleaned_json = cleaned_json[7:]
            if cleaned_json.endswith('```'):
                cleaned_json = cleaned_json[:-3]
            cleaned_json = cleaned_json.strip()
            
            # Parse and validate
            task_understanding = json.loads(cleaned_json)
            if not isinstance(task_understanding, dict):
                raise ValueError("Task understanding must be a dictionary")
                
            # Store for later use
            self.current_task_context = task_understanding
            return task_understanding

        except Exception as e:
            logger.error(f"Failed to understand task: {str(e)}")
            return {
                "type": "simple",
                "components": [task],
                "dependencies": {},
                "requirements": {},
                "validation_needs": [],
                "temporal_aspect": "none",
                "output_format": "analysis"
            }

    def adapt_to_future_tasks(self, new_task):
        # Logic to adapt based on previous tasks
        return f"Adapting to new task: {new_task}"