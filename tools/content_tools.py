import os
import google.generativeai as genai
from typing import Dict, Any, Optional
from .base import BaseTool
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ContentGeneratorTool(BaseTool):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro',
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        self.topic_analyzers = {
            'technical': self._create_technical_prompt,
            'educational': self._create_educational_prompt,
            'analysis': self._create_analysis_prompt,
            'general': self._create_general_prompt
        }

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate content based on the query"""
        try:
            logger.debug(f"Analyzing query type: {query}")
            topic_type = self._analyze_topic_type(query)
            prompt_creator = self.topic_analyzers.get(topic_type, self.topic_analyzers['general'])
            
            prompt = prompt_creator(query)
            logger.debug(f"Using {topic_type} prompt template")

            # Generate initial content
            response = self.model.generate_content(prompt)
            
            if not response.text:
                return {"success": False, "error": "No content generated"}

            # Enhance content with additional context
            enhanced_content = await self._enhance_content(response.text, query)
            
            # Use standard datetime instead of genai's datetime_helpers
            current_time = datetime.now().isoformat()
            
            return {
                "success": True,
                "content": {
                    "content": enhanced_content,
                    "type": "article",
                    "confidence": 0.8,
                    "metadata": {
                        "format": "markdown",
                        "topic": query,
                        "topic_type": topic_type,
                        "generated_at": current_time
                    }
                }
            }

        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Content generation failed: {str(e)}",
            }

    def _analyze_topic_type(self, query: str) -> str:
        """Analyze the type of content needed"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['code', 'programming', 'algorithm', 'technical']):
            return 'technical'
        elif any(term in query_lower for term in ['learn', 'guide', 'tutorial', 'how to']):
            return 'educational'
        elif any(term in query_lower for term in ['analyze', 'compare', 'review', 'pros and cons']):
            return 'analysis'
        return 'general'

    def _create_technical_prompt(self, query: str) -> str:
        return f"""Write a technical blog post about: {query}

        Requirements:
        1. Start with a technical overview
        2. Include code examples where relevant
        3. Explain technical concepts clearly
        4. Add implementation details
        5. Include best practices
        6. Add error handling considerations
        7. Conclude with practical applications

        Use proper Markdown formatting including code blocks.
        """

    def _create_educational_prompt(self, query: str) -> str:
        return f"""Write an educational guide about: {query}

        Requirements:
        1. Start with a clear learning objective
        2. Break down complex concepts
        3. Include practical examples
        4. Add step-by-step instructions
        5. Include key takeaways
        6. Add common pitfalls to avoid
        7. Conclude with practice suggestions

        Use proper Markdown formatting with clear sections and examples.
        """

    def _create_analysis_prompt(self, query: str) -> str:
        return f"""Write an analytical article about: {query}

        Requirements:
        1. Present a clear overview
        2. Analyze key components
        3. Compare different aspects
        4. Provide data and evidence
        5. Discuss pros and cons
        6. Include expert perspectives
        7. Draw meaningful conclusions

        Use proper Markdown formatting with data presentation.
        """

    def _create_general_prompt(self, query: str) -> str:
        return f"""Write an informative article about: {query}

        Requirements:
        1. Start with an engaging introduction
        2. Cover main topics comprehensively
        3. Include relevant examples
        4. Back claims with evidence
        5. Address common questions
        6. Provide actionable insights
        7. End with a strong conclusion

        Use proper Markdown formatting for readability.
        """

    async def _enhance_content(self, content: str, query: str) -> str:
        """Enhance content with additional context and formatting"""
        # Add table of contents for longer content
        if len(content.split('\n')) > 20:
            content = self._add_table_of_contents(content)
            
        # Add metadata section
        content += f"\n\n---\n*Generated for topic: {query}*\n"
        content += f"*Last updated: {datetime.now().strftime('%Y-%m-%d')}*\n"
        
        return content

    def _add_table_of_contents(self, content: str) -> str:
        """Add table of contents to content"""
        import re
        headers = re.findall(r'^#{1,3} (.+)$', content, re.MULTILINE)
        if headers:
            toc = "\n## Table of Contents\n\n"
            for i, header in enumerate(headers, 1):
                toc += f"{i}. [{header}](#{header.lower().replace(' ', '-')})\n"
            return toc + "\n" + content
        return content

    def get_description(self) -> str:
        return "Generates blog posts and articles using Gemini Pro"
