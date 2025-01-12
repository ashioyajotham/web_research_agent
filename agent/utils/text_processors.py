from typing import List, Set, Dict, Any
import re
from collections import Counter
import json

class TextProcessor:
    @staticmethod
    def extract_json_blocks(text: str) -> List[Dict[str, Any]]:
        """Extract JSON objects from text"""
        json_pattern = r'\{[^{}]*\}'
        results = []
        
        for match in re.finditer(json_pattern, text):
            try:
                json_obj = json.loads(match.group())
                results.append(json_obj)
            except json.JSONDecodeError:
                continue
                
        return results
    
    @staticmethod
    def extract_code_blocks(text: str) -> List[str]:
        """Extract code blocks from text"""
        code_block_pattern = r'```[\w]*\n(.*?)```'
        return [
            block.strip() 
            for block in re.findall(code_block_pattern, text, re.DOTALL)
        ]
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    @staticmethod
    def summarize(text: str, max_length: int = 1000) -> str:
        """Create a summary of text"""
        # Simple summarization by keeping first few sentences
        sentences = re.split(r'[.!?]+', text)
        summary = []
        length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            length += len(sentence)
            if length > max_length:
                break
                
            summary.append(sentence)
            
        return '. '.join(summary) + ('...' if length > max_length else '.')

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        # Normalize whitespace
        return text.strip()
