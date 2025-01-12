from typing import Any, Dict, List, Optional
import re
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]

class Validator:
    @staticmethod
    def validate_json_response(response: Any) -> ValidationResult:
        """Validate JSON response format"""
        errors = []
        
        if not isinstance(response, dict):
            return ValidationResult(False, ["Response must be a dictionary"])
            
        if "thought" not in response:
            errors.append("Missing 'thought' field")
            
        if "answer" in response:
            if "confidence" not in response:
                errors.append("Answer requires confidence score")
        elif "tool" in response:
            if "input" not in response:
                errors.append("Tool usage requires input")
        else:
            errors.append("Response must contain either 'answer' or 'tool'")
            
        return ValidationResult(len(errors) == 0, errors)
    
    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """Validate URL format"""
        url_pattern = r'^https?:\/\/([\w\d-]+\.)*[\w-]+\.[a-zA-Z]+(?:\/[\w\d-.,/?=&%#+]*)?$'
        valid = bool(re.match(url_pattern, url))
        return ValidationResult(
            valid,
            [] if valid else ["Invalid URL format"]
        )
    
    @staticmethod
    def validate_tool_input(tool_name: str, input_data: Dict[str, Any]) -> ValidationResult:
        """Validate tool input data"""
        errors = []
        
        if not isinstance(input_data, dict):
            return ValidationResult(False, ["Input must be a dictionary"])
            
        # Tool-specific validation
        if tool_name == "google_search":
            if "query" not in input_data:
                errors.append("Search requires 'query' field")
        elif tool_name == "web_scraper":
            if "url" not in input_data:
                errors.append("Scraper requires 'url' field")
            elif not Validator.validate_url(input_data["url"]).valid:
                errors.append("Invalid URL format")
        elif tool_name == "code_analysis":
            if "command" not in input_data:
                errors.append("Code analysis requires 'command' field")
            if "code" not in input_data:
                errors.append("Code analysis requires 'code' field")
                
        return ValidationResult(len(errors) == 0, errors)
