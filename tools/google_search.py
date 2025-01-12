import os
import requests
from typing import Dict, List
from .base import BaseTool

class GoogleSearchTool(BaseTool):
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable not set")
        
    def execute(self, query: str) -> str:
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            'q': query,
            'num': 10
        }
        
        try:
            response = requests.post(
                'https://google.serper.dev/search',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            results = response.json()
            
            formatted_results = []
            for item in results.get('organic', []):
                formatted_results.append(
                    f"Title: {item['title']}\n"
                    f"Link: {item['link']}\n"
                    f"Snippet: {item['snippet']}\n"
                )
            
            return "\n".join(formatted_results)
        except Exception as e:
            return f"Error performing Google search: {str(e)}"
    
    def get_description(self) -> str:
        return "Searches Google and returns relevant web results. Input should be a search query."
