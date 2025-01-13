from typing import Optional, Dict, Any
from .base import BaseTool
import google.generativeai as genai
from datetime import datetime

class ContentGeneratorTool(BaseTool):
    """Tool for generating blog posts and articles"""
    
    def __init__(self):
        super().__init__()
        self.model = genai.GenerativeModel('gemini-pro')
        
    def get_description(self) -> str:
        return """Generates content like blog posts, articles and technical documentation.
Features:
- Well-structured content with headings
- Technical accuracy with examples
- Beginner-friendly explanations
- Proper citations and references
- Markdown formatting
        """

    async def execute(self, task: str, **kwargs) -> Dict[str, Any]:
        """Generate content based on task"""
        try:
            if not task:
                return {
                    "success": False,
                    "error": "No content topic provided",
                    "content": None
                }

            # Enhanced prompt for content generation
            prompt = f"""Create a comprehensive article about: {task}

            Requirements:
            1. Clear structure with headings
            2. Code snippets and examples where relevant
            3. Technical accuracy and depth
            4. Beginner-friendly explanations
            5. Citations and references where appropriate

            Format the content in Markdown with:
            - Headers using #
            - Code blocks using ```
            - Lists and bullet points
            - Bold and italic for emphasis
            """
            

            response = self.model.generate_content(prompt)
            
            if not response.text:
                return {
                    "success": False,
                    "error": "No content generated",
                    "content": None
                }
                
            return {
                "success": True,
                "content": response.text,
                "type": "article",
                "confidence": 0.8,
                "metadata": {
                    "format": "markdown",
                    "topic": task,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
