from abc import ABC, abstractmethod
import os
import json
import asyncio
from typing import Optional, Dict, List, Any
import google.generativeai as genai
from utils.helpers import logger, truncate_text
import time

class LLMInterface(ABC):
    """Abstract base class for LLM implementations"""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text response from prompt"""
        pass
    
    @abstractmethod
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Generate code from prompt"""
        pass

class RateLimiter:
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.timestamps = []

    async def acquire(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t <= self.period]
        
        if len(self.timestamps) >= self.calls:
            sleep_time = self.timestamps[0] + self.period - now
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.timestamps.append(now)

class GeminiLLM(LLMInterface):
    def __init__(self, api_key: Optional[str] = None, 
                 max_retries: int = 3,
                 temperature: float = 0.7):
        self.api_key = api_key or self._get_gemini_api_key()
        self.max_retries = max_retries
        self.temperature = temperature
        self.rate_limiter = RateLimiter(calls=60, period=60.0)  # 60 calls per minute
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model with configurations
        generation_config = {
            "temperature": self.temperature,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        self.model = genai.GenerativeModel(
            'gemini-1.5-pro',
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        self.code_model = genai.GenerativeModel(
            'gemini-1.5-pro',
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
    @staticmethod
    def _get_gemini_api_key() -> str:
        """Get Gemini API key from environment"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return api_key

    async def generate(self, prompt: str) -> str:
        """Generate text response using Gemini with retry logic"""
        for attempt in range(self.max_retries):
            try:
                await self.rate_limiter.acquire()
                response = await self.model.generate_content_async(prompt)
                return response.text.strip()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Gemini generation failed after {self.max_retries} attempts: {str(e)}")
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Generate code using Gemini with language-specific formatting"""
        try:
            code_prompt = f"""
            Write code in {language} for the following task.
            Only return the code, no explanations.
            Include proper error handling and comments.
            Don't include markdown code blocks.

            Task: {prompt}
            """
            response = await self.model.generate_content_async(code_prompt)
            return self._clean_code_response(response.text)
        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}")
            raise

    async def analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code for potential improvements and security issues"""
        try:
            analysis_prompt = f"""
            Analyze this code for:
            1. Potential security vulnerabilities
            2. Performance improvements
            3. Best practice violations
            4. Code smells
            
            Return as JSON with these categories.
            Code to analyze:
            {code}
            """
            response = await self.model.generate_content_async(analysis_prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Code analysis failed: {str(e)}")
            raise

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize text using Gemini"""
        text = truncate_text(text, 4000)  # Prevent context length issues
        try:
            prompt = f"""
            Summarize the following text concisely in {max_length} characters or less.
            Focus on key information and maintain coherence.
            Text: {text}
            """
            return await self.generate(prompt)
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            raise

    async def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        """Extract key points from text with improved formatting"""
        text = truncate_text(text, 4000)
        try:
            prompt = f"""
            Extract exactly {num_points} main points from this text.
            Format each point as a clear, concise statement.
            Text: {text}
            """
            response = await self.model.generate_content_async(prompt)
            return [point.strip('- ') for point in response.text.strip().split('\n') if point.strip()]
        except Exception as e:
            logger.error(f"Key points extraction failed: {str(e)}")
            raise

    def _clean_code_response(self, text: str) -> str:
        """Clean up code response by removing markdown and extra whitespace"""
        lines = text.strip().split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines[-1].startswith('```'):
            lines = lines[:-1]
        # Remove language identifier if present
        if lines[0].startswith('python') or lines[0].startswith('javascript'):
            lines = lines[1:]
        return '\n'.join(line for line in lines if line.strip()).strip()

    def _format_code_response(self, code: str, language: str) -> str:
        """Format code response with proper indentation and styling"""
        # Remove any markdown code blocks if present
        code = code.replace('```' + language, '').replace('```', '').strip()
        
        # Add proper newlines between functions/classes
        if language == "python":
            code = code.replace('\n\n\n', '\n\n')
            
        return code