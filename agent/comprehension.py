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
        1. "task_type": The general category of the task (e.g., "information_gathering", "code_generation", "problem_solving", "data_analysis")
        2. "requires_coding": Boolean (true/false) indicating if this task actually requires writing or generating code
        3. "key_entities": List of important entities, concepts, or technologies mentioned in the task
        4. "search_queries": Suggested search queries to gather information for this task
        5. "required_information": Types of information that need to be gathered
        6. "presentation_format": How the information should be presented (e.g., "table", "list", "report", "code", "summary")
        7. "expected_output": What the final output should look like
        
        For the "requires_coding" field, only mark as true if the task explicitly asks for:
        - Writing a program, script, or function
        - Implementing an algorithm 
        - Creating code in a specific language
        
        Do NOT mark as true if the task is just about:
        - Finding information
        - Creating a report
        - Showing data in a table/chart
        - Summarizing information
        
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
        if (len(content) <= max_length):
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
    
    def extract_entities(self, text, entity_types=None):
        """
        Extract named entities from text content.
        
        Args:
            text (str): The text to analyze
            entity_types (list, optional): Types of entities to extract (e.g., 'person', 'organization', 'role')
                If None, extract all entity types
                
        Returns:
            dict: Dictionary of entity types and their extracted values
        """
        logger.info(f"Extracting entities from text of length {len(text)}")
        
        # Default entity types if none specified
        if entity_types is None:
            entity_types = ['person', 'organization', 'role', 'location', 'date', 'title']
        
        # Cap text length to avoid token limits
        text_sample = text[:25000] if len(text) > 25000 else text
        
        prompt = f"""
        Extract the following entity types from the text below:
        {', '.join(entity_types)}
        
        For each entity type, provide a list of unique values found in the text.
        If multiple entities refer to the same thing (e.g., "John Smith" and "Mr. Smith"), list them together.
        For role entities, include the person and organization they relate to when possible.
        
        TEXT:
        {text_sample}
        
        Return the results as a JSON object with entity types as keys and arrays of found entities as values.
        For roles, include the format "role: person @ organization" when that information is available.
        
        Example format:
        {{
            "person": ["John Smith", "Jane Doe"],
            "organization": ["Acme Corp", "Epoch AI"],
            "role": ["CEO: John Smith @ Acme Corp", "COO: Jane Doe @ Epoch AI"]
        }}
        
        Only include entity types that have at least one match. Return ONLY the JSON without additional text.
        """
        
        try:
            response = self.model.generate_content(prompt)
            entities = self._extract_json(response.text)
            logger.info(f"Extracted entities: {entities}")
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {entity_type: [] for entity_type in entity_types}
    
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
