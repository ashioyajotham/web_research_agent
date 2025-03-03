from typing import Dict, List, Optional, Any
from utils.helpers import logger
import json
import re

class Comprehension:
    def __init__(self, llm):
        self.llm = llm
        self.context = {}

    async def analyze_task(self, task: str) -> Dict:
        """Analyze task and break it down into subtasks"""
        prompt = f"""
        Analyze this task and break it down into subtasks:
        {task}
        
        Return subtasks in this format:
        - Subtask 1 description
        - Subtask 2 description
        etc.
        
        Focus on search and analysis steps needed.
        """
        
        try:
            response = await self.llm.generate(prompt)
            # Handle different response formats
            content = response if isinstance(response, str) else getattr(response, 'text', str(response))
            
            # Extract subtasks using regex for more robust parsing
            subtask_pattern = r'[-*•]\s*(.+?)(?=\n[-*•]|\n\n|$)'
            subtasks = re.findall(subtask_pattern, content, re.MULTILINE)
            
            # Clean and validate subtasks
            valid_subtasks = [
                subtask.strip()
                for subtask in subtasks
                if subtask.strip() and len(subtask.strip()) > 10
            ]
            
            if not valid_subtasks:
                # Fallback to simple line-based extraction
                valid_subtasks = [
                    line.strip('- *•').strip()
                    for line in content.split('\n')
                    if line.strip().startswith(('-', '*', '•'))
                ]
            
            logger.info(f"Generated {len(valid_subtasks)} subtasks")
            return {'subtasks': valid_subtasks}
            
        except Exception as e:
            logger.error(f"Task analysis failed: {str(e)}")
            # Return default subtasks instead of empty list
            return {
                'subtasks': [
                    "Search for relevant information",
                    "Analyze and filter results",
                    "Compile findings into required format"
                ]
            }

    def _extract_content(self, response: Any) -> str:
        """Extract text content from LLM response"""
        if isinstance(response, str):
            return response
        elif hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'content'):
            return response.content
        else:
            return str(response)

    async def analyze_results(self, description: str, task_context: Dict) -> Dict:
        """Analyze and filter search results"""
        try:
            if not self.context.get('search_results'):
                return {'status': 'no_results'}
                
            prompt = f"""
            Analyze these search results for relevant information about:
            {description}
            
            Context: {json.dumps(task_context)}
            Results: {json.dumps(self.context['search_results'])}
            
            Extract and summarize key findings.
            """
            
            response = await self.llm.generate(prompt)
            content = self._extract_content(response)
            
            return {
                'status': 'success',
                'analysis': content,
                'source_count': len(self.context.get('search_results', []))
            }
        except Exception as e:
            logger.error(f"Results analysis failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def synthesize_partial(self, description: str, task_context: Dict) -> Dict:
        """Synthesize partial results during task execution"""
        try:
            if not self.context.get('analyzed_results'):
                return {'status': 'no_analysis'}
                
            prompt = f"""
            Create a partial synthesis of the analyzed information for:
            {description}
            
            Context: {json.dumps(task_context)}
            Analysis: {json.dumps(self.context['analyzed_results'])}
            
            Provide a structured summary of findings so far.
            """
            
            response = await self.llm.generate(prompt)
            content = self._extract_content(response)
            
            return {
                'status': 'success',
                'synthesis': content
            }
        except Exception as e:
            logger.error(f"Partial synthesis failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def synthesize_results(self, results: List[Dict]) -> str:
        """Create final synthesis of all results"""
        try:
            if not results:
                return "No results to synthesize"
                
            # Store results in context
            self.context['final_results'] = results
            
            prompt = f"""
            Create a final synthesis of all results:
            {json.dumps(results)}
            
            Provide a well-structured response that:
            1. Summarizes key findings
            2. Highlights important connections
            3. Presents conclusions
            """
            
            response = await self.llm.generate(prompt)
            return self._extract_content(response)
            
        except Exception as e:
            logger.error(f"Final synthesis failed: {str(e)}")
            return f"Synthesis failed: {str(e)}"

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
        """Analyze task structure and requirements dynamically"""
        try:
            # Extract key task characteristics
            characteristics = await self._extract_task_characteristics(task)
            
            # Build task context
            task_context = {
                "type": characteristics.get('type', 'simple'),
                "components": characteristics.get('components', []),
                "temporal_aspect": characteristics.get('temporal_aspect', 'current'),
                "requirements": {
                    "data_needed": characteristics.get('data_needed', []),
                    "source_types": characteristics.get('source_types', []),
                    "validation_criteria": characteristics.get('validation_criteria', [])
                },
                "constraints": characteristics.get('constraints', {}),
                "output_format": characteristics.get('output_format', 'analysis')
            }

            return task_context

        except Exception as e:
            logger.error(f"Failed to understand task: {str(e)}")
            return self._get_default_context(task)

    async def _extract_task_characteristics(self, task: str) -> Dict:
        """Extract task characteristics using LLM with improved error handling"""
        prompt = f"""Analyze this task and identify its key characteristics:
Task: {task}

Return a JSON object with these dynamic features:
- type: The general type of task (research/analysis/comparison/etc)
- components: Key elements that need to be investigated
- temporal_aspect: Time relevance (historical/current/future)
- data_needed: Types of information required
- source_types: Preferred source categories
- validation_criteria: How to verify information
- constraints: Any limitations or requirements
- output_format: How results should be presented"""

        try:
            response = await self.llm.generate(prompt)
            content = response if isinstance(response, str) else getattr(response, 'text', str(response))
            
            # Try to parse JSON from response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, extract characteristics using regex
                characteristics = {}
                patterns = {
                    'type': r'type"?\s*:?\s*"?([^",\n]+)',
                    'temporal_aspect': r'temporal_aspect"?\s*:?\s*"?([^",\n]+)',
                    'output_format': r'output_format"?\s*:?\s*"?([^",\n]+)'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        characteristics[key] = match.group(1).strip()
                
                return characteristics or self._get_default_characteristics()
                
        except Exception as e:
            logger.error(f"Failed to extract task characteristics: {str(e)}")
            return self._get_default_characteristics()

    def _get_default_characteristics(self) -> Dict:
        """Provide default task characteristics"""
        return {
            "type": "research",
            "components": ["information gathering", "analysis"],
            "temporal_aspect": "current",
            "data_needed": ["facts", "sources"],
            "source_types": ["web"],
            "validation_criteria": ["multiple sources"],
            "constraints": {},
            "output_format": "summary"
        }

    def adapt_to_future_tasks(self, new_task):
        # Logic to adapt based on previous tasks
        return f"Adapting to new task: {new_task}"

class ResultProcessor:
    def __init__(self):
        self.processors = {
            'search': self._process_search,
            'list': self._process_list,
            'analysis': self._process_analysis
        }
        
    async def process(self, task_type: str, raw_results: List[Dict]) -> Dict:
        processor = self.processors.get(task_type, self._process_default)
        return await processor(raw_results)