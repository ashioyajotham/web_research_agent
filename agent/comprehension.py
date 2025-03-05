from utils.logger import get_logger
from config.config import get_config
import google.generativeai as genai
import json
import re

logger = get_logger(__name__)

class Comprehension:
    """Text understanding and reasoning capabilities."""
    
    def __init__(self):
        """Initialize the comprehension module."""
        config = get_config()
        genai.configure(api_key=config.get("gemini_api_key"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name
    
    def analyze_task(self, task_description):
        """
        Analyze a task description to understand what's being asked.
        
        Args:
            task_description (str): The task description
            
        Returns:
            dict: Analysis of the task
        """
        logger.info(f"Analyzing task: {task_description}")
        
        prompt = f"""
        Analyze the following task and break it down into components:
        
        TASK: {task_description}
        
        Please provide a structured analysis in JSON format with the following fields:
        1. "task_type": The general category of the task (e.g., "information_gathering", "code_generation", "problem_solving", etc.)
        2. "key_entities": List of important entities, concepts, or technologies mentioned in the task
        3. "search_queries": Suggested search queries to gather information for this task
        4. "required_information": Types of information that need to be gathered
        5. "expected_output": What the final output should look like (e.g., code, report, analysis, etc.)
        
        Return ONLY the JSON without additional explanation or formatting.
        """
        
        try:
            # Updated API call format
            response = self.model.generate_content(prompt)
            analysis = self._extract_json(response.text)
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing task: {str(e)}")
            # Return a basic analysis if LLM fails
            return {
                "task_type": "general_research",
                "key_entities": [task_description.split()[:3]],
                "search_queries": [task_description],
                "required_information": ["general information"],
                "expected_output": "report"
            }
    
    def summarize_content(self, content, max_length=500):
        """
        Summarize content to a specified maximum length.
        
        Args:
            content (str): Content to summarize
            max_length (int): Approximate maximum length of summary
            
        Returns:
            str: Summarized content
        """
        if len(content) <= max_length:
            return content
        
        prompt = f"""
        Summarize the following content in about {max_length} characters:
        
        {content[:10000]}  # Limit input to avoid token limits
        
        Provide only the summary without additional commentary.
        """
        
        try:
            # Updated API call format
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error summarizing content: {str(e)}")
            # Simple fallback summarization
            return content[:max_length] + "..."
    
    def extract_relevant_information(self, content, query):
        """
        Extract parts of the content most relevant to the query.
        
        Args:
            content (str): Content to analyze
            query (str): Query to extract information for
            
        Returns:
            str: Relevant information
        """
        prompt = f"""
        Extract the parts of the following content that are most relevant to the query:
        
        QUERY: {query}
        
        CONTENT:
        {content[:10000]}  # Limit input to avoid token limits
        
        Provide only the relevant extracted information without additional commentary.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error extracting information: {str(e)}")
            return "Failed to extract relevant information."
    
    def _extract_json(self, text):
        """Extract and parse JSON from text."""
        # Try to find JSON within code blocks
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'({[\s\S]*})', text)
            if (json_match):
                json_str = json_match.group(1)
            else:
                raise ValueError("Could not extract JSON from response")
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common JSON errors
            json_str = json_str.replace("'", '"')
            # Remove any non-JSON content
            clean_json = re.sub(r'(?<!["{\s,:])\s*//.*?(?=\n|$)', '', json_str)
            return json.loads(clean_json)
