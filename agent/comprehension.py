from models.llm import LLMInterface
from typing import List, Dict, Any
from utils.helpers import logger
import json
import re

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
            # Get task context from knowledge base
            task_context = self.knowledge_base[-1] if self.knowledge_base else {}
            
            # Build dynamic prompt based on task requirements
            prompt = f"""Synthesize these research results into a comprehensive response:

Research Data:
{'\n'.join(results)}

Task Context:
{json.dumps(task_context, indent=2)}

Synthesis Requirements:
1. Format output in clear Markdown with appropriate headers
2. Provide specific sources for factual claims or quotes
3. Adapt structure based on content type (data, statements, analysis, etc.)
4. Include relevant context (dates, locations, organizations)
5. Highlight key uncertainties or data gaps
6. Add a "Methodology" section explaining how conclusions were reached
7. End with a "Sources" section listing references with quality indicators

Focus on {task_context.get('main_objective', 'providing comprehensive analysis')}
"""
            response = await self.llm.generate(prompt)
            
            # Ensure minimum response structure
            if not any(header in response for header in ['# ', '## ', '**']):
                response = f"# Research Summary\n\n{response}"
            
            if "Sources:" not in response:
                found_sources = self._extract_sources(results)
                response += "\n\n## Sources\n" + "\n".join(f"- {source}" for source in found_sources)
                
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