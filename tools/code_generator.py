from typing import Dict, Any, Optional
from .tool_registry import BaseTool
from utils.logger import get_logger
from config.config import get_config
import google.generativeai as genai

logger = get_logger(__name__)

class CodeGeneratorTool(BaseTool):
    """Tool for generating and working with code using Gemini."""
    
    def __init__(self):
        """Initialize the code generator tool."""
        super().__init__(
            name="code",
            description="Generates, explains, debugs, or optimizes code based on the prompt"
        )
        config = get_config()
        genai.configure(api_key=config.get("gemini_api_key"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name
        
    def execute(self, parameters: Dict[str, Any], memory: Any) -> str:
        """
        Execute the code generation tool with the given parameters.
        
        Args:
            parameters (dict): Parameters for the tool
                - prompt (str): The main prompt describing what code to generate
                - language (str, optional): Programming language to use
                - operation (str, optional): Type of operation (generate, debug, explain, optimize, convert)
                - existing_code (str, optional): Existing code to work with for debug/explain/optimize
                - target_language (str, optional): Target language for code conversion
            memory (Memory): Agent's memory
            
        Returns:
            str: Generated code or explanation
        """
        prompt = parameters.get("prompt")
        if not prompt:
            return "Error: No prompt provided for code generation"
        
        language = parameters.get("language", "python")
        operation = parameters.get("operation", "generate")
        existing_code = parameters.get("existing_code", "")
        target_language = parameters.get("target_language", "")
        
        try:
            if operation == "generate":
                return self._generate_code(prompt, language)
            elif operation == "debug":
                return self._debug_code(prompt, existing_code, language)
            elif operation == "explain":
                return self._explain_code(existing_code, language)
            elif operation == "optimize":
                return self._optimize_code(existing_code, prompt, language)
            elif operation == "convert":
                return self._convert_code(existing_code, language, target_language)
            else:
                return f"Error: Unknown operation '{operation}'. Supported operations: generate, debug, explain, optimize, convert"
        except Exception as e:
            logger.error(f"Error in code generation: {str(e)}")
            return f"Error generating code: {str(e)}"
    
    def _generate_code(self, prompt: str, language: str) -> str:
        """Generate code based on a prompt."""
        # Create combined prompt with system and user instructions
        combined_prompt = f"""You are an expert {language} programmer. 
        Generate well-commented, efficient, and readable {language} code based on the user's requirements.
        Include docstrings, error handling, and follow best practices for {language}.
        Return ONLY the code without additional explanation.
        
        Generate {language} code for the following: {prompt}
        """
        
        # Updated API call format
        response = self.model.generate_content(combined_prompt)
        
        code = self._extract_code_from_response(response.text, language)
        return code
    
    def _debug_code(self, prompt: str, code: str, language: str) -> str:
        """Debug existing code based on a description of the issue."""
        # Create combined prompt
        combined_prompt = f"""You are an expert {language} debugger.
        Analyze the provided code and fix any issues based on the problem description.
        Explain the issues you found and how you fixed them.
        
        Problem description: {prompt}
        
        Code to debug:
        ```{language}
        {code}
        ```
        """
        
        # Updated API call format
        response = self.model.generate_content(combined_prompt)
        
        return response.text
    
    def _explain_code(self, code: str, language: str) -> str:
        """Provide an explanation for what the code does."""
        # Create combined prompt
        combined_prompt = f"""You are an expert code explainer. 
        Analyze the provided code and explain what it does in a clear, detailed manner.
        
        Explain the following {language} code:
        ```{language}
        {code}
        ```
        """
        
        # Updated API call format
        response = self.model.generate_content(combined_prompt)
        
        return response.text
    
    def _optimize_code(self, code: str, requirements: str, language: str) -> str:
        """Optimize existing code for better performance or readability."""
        # Create combined prompt
        combined_prompt = f"""You are an expert {language} optimizer.
        Analyze the provided code and optimize it according to the requirements.
        Provide both the optimized code and an explanation of your changes.
        
        Optimization requirements: {requirements}
        
        Code to optimize:
        ```{language}
        {code}
        ```
        """
        
        # Updated API call format
        response = self.model.generate_content(combined_prompt)
        
        return response.text
    
    def _convert_code(self, code: str, source_language: str, target_language: str) -> str:
        """Convert code from one language to another."""
        # Create combined prompt
        combined_prompt = f"""You are an expert programmer. 
        Convert the provided {source_language} code to equivalent {target_language} code.
        Ensure the converted code maintains the same functionality.
        Include any necessary language-specific adjustments.
        
        Convert this {source_language} code to {target_language}:
        ```{source_language}
        {code}
        ```
        """
        
        # Updated API call format
        response = self.model.generate_content(combined_prompt)
        
        converted_code = self._extract_code_from_response(response.text, target_language)
        return converted_code
    
    def _extract_code_from_response(self, text: str, language: str) -> str:
        """Extract code from the LLM response."""
        import re
        
        # First try to extract code blocks with language marker
        pattern = f"```{language}(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Try without language marker
        pattern = r"```(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks found, return the raw text
        return text.strip()
