import os
from typing import Dict, Any, Optional, List, Tuple
from .base import BaseTool
import asyncio
from datetime import datetime
import logging
import google.generativeai as genai
from dataclasses import dataclass
from enum import Enum, auto

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ContentType(Enum):
    TECHNICAL = auto()
    EDUCATIONAL = auto()
    ANALYSIS = auto()
    GENERAL = auto()
    CREATIVE = auto()
    RESEARCH = auto()

@dataclass
class ContentStrategy:
    content_type: ContentType
    structure: List[str]
    style_guide: Dict[str, Any]
    requirements: List[str]
    formatting: Dict[str, Any]

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
        
        # Dynamic content strategies
        self.strategies: Dict[ContentType, ContentStrategy] = self._initialize_strategies()
        
        # Learning system for content patterns
        self.pattern_memory: Dict[str, List[Dict[str, Any]]] = {}
        
        # Adaptive formatting rules
        self.formatting_rules = self._initialize_formatting_rules()

    def get_description(self) -> str:
        """Return tool description"""
        return "A content generation tool that creates high-quality content with dynamic adaptation based on context and requirements"

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata"""
        return {
            "name": "content_generator",
            "type": "content_creation",
            "version": "1.0",
            "capabilities": [
                "technical_writing",
                "educational_content",
                "analysis_reports",
                "research_summaries",
                "adaptive_formatting"
            ]
        }

    def _initialize_strategies(self) -> Dict[ContentType, ContentStrategy]:
        """Initialize flexible content strategies"""
        return {
            ContentType.TECHNICAL: ContentStrategy(
                content_type=ContentType.TECHNICAL,
                structure=["overview", "technical_details", "implementation", "examples", "best_practices"],
                style_guide={"tone": "technical", "depth": "high", "code_examples": True},
                requirements=["code_samples", "technical_accuracy", "implementation_details"],
                formatting={"code_blocks": True, "diagrams": True}
            ),
            ContentType.EDUCATIONAL: ContentStrategy(
                content_type=ContentType.EDUCATIONAL,
                structure=["learning_objectives", "concepts", "examples", "practice", "summary"],
                style_guide={"tone": "instructional", "depth": "progressive", "examples": True},
                requirements=["clear_explanations", "practical_exercises", "key_takeaways"],
                formatting={"sections": True, "highlights": True}
            ),
            # ...existing code for other content types...
        }

    def _initialize_formatting_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default formatting rules"""
        return {
            'technical': {
                'code_blocks': {
                    'style': 'fenced',
                    'language_hint': True
                },
                'headers': {
                    'style': 'atx',  # # Style headers
                    'max_level': 3
                }
            },
            'educational': {
                'sections': {
                    'clear_breaks': True,
                    'numbered': True
                },
                'highlights': {
                    'bold_key_terms': True,
                    'box_definitions': True
                }
            },
            'general': {
                'paragraphs': {
                    'max_length': 500,
                    'line_breaks': True
                },
                'lists': {
                    'bullet_style': '-',
                    'max_nesting': 2
                }
            }
        }

    async def execute(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Execute content operations with proper async handling"""
        if not query:
            return {
                'success': False,
                'error': 'Query parameter is required'
            }

        try:
            operation = kwargs.get('operation', 'generate')
            context = kwargs.get('context', {})

            if operation == 'analyze':
                return await self._analyze_content(query, **context)
            elif operation == 'summarize':
                return await self._summarize_content(query, **context)
            else:
                return await self._generate_content(query, **context)

        except Exception as e:
            self.logger.error(f"Content operation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _analyze_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Analyze content using Gemini"""
        prompt = f"""Analyze the following content and provide key insights:
        Content: {content}
        Provide:
        1. Main topics
        2. Key points
        3. Sentiment
        4. Relevant metrics or data points
        """
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt
        )
        
        if not response or not response.text:
            return {"success": False, "error": "No analysis generated"}
            
        return {
            "success": True,
            "output": {
                "analysis": response.text,
                "type": "content_analysis"
            }
        }

    async def _summarize_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Summarize content using Gemini"""
        max_length = kwargs.get('max_length', 500)
        prompt = f"""Provide a concise summary of the following content in no more than {max_length} characters:
        {content}"""
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt
        )
        
        if not response or not response.text:
            return {"success": False, "error": "No summary generated"}
            
        return {
            "success": True,
            "output": {
                "summary": response.text,
                "type": "content_summary"
            }
        }

    async def _generate_content(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate content with dynamic adaptation"""
        try:
            # Analyze query and context
            content_type = self._analyze_content_requirements(query, kwargs)
            strategy = self.strategies[content_type]
            
            # Build dynamic prompt
            prompt = self._build_dynamic_prompt(query, strategy, kwargs)
            
            # Generate initial content using async execution
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if not response or not response.text:
                return {"success": False, "error": "No content generated"}

            # Process and enhance content
            enhanced_content = await self._process_content(
                response.text,
                strategy,
                context=kwargs.get('context', {})
            )
            
            # Learn from generation
            self._update_pattern_memory(query, enhanced_content, content_type)
            
            return {
                "success": True,
                "content": {
                    "content": enhanced_content,
                    "type": content_type.name.lower(),
                    "confidence": self._calculate_confidence(enhanced_content, strategy),
                    "metadata": self._generate_metadata(query, content_type, kwargs)
                }
            }

        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Content generation failed: {str(e)}",
            }

    def _analyze_content_requirements(self, query: str, context: Dict) -> ContentType:
        """Dynamically analyze content requirements"""
        query_features = self._extract_query_features(query)
        context_features = self._extract_context_features(context)
        
        # Use pattern memory to improve type detection
        learned_patterns = self._get_relevant_patterns(query)
        
        return self._determine_content_type(query_features, context_features, learned_patterns)

    def _extract_query_features(self, query: str) -> Dict[str, Any]:
        """Extract relevant features from the query"""
        return {
            'length': len(query.split()),
            'type': self._detect_query_type(query),
            'complexity': self._calculate_complexity(query),
            'topics': self._extract_topics(query),
            'requirements': self._extract_requirements(query)
        }

    def _detect_query_type(self, query: str) -> str:
        """Detect the type of query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['create', 'generate', 'write']):
            return 'generation'
        elif any(word in query_lower for word in ['analyze', 'examine', 'study']):
            return 'analysis'
        elif any(word in query_lower for word in ['summarize', 'brief']):
            return 'summary'
        return 'general'

    def _calculate_complexity(self, query: str) -> float:
        """Calculate query complexity score"""
        words = query.split()
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        unique_words = len(set(words))
        
        return min((avg_word_length * 0.3 + unique_words * 0.7) / 10, 1.0)

    def _extract_topics(self, query: str) -> List[str]:
        """Extract main topics from query"""
        words = query.lower().split()
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'with'}
        return [word for word in words if word not in stop_words and len(word) > 3]

    def _extract_requirements(self, query: str) -> List[str]:
        """Extract specific requirements from query"""
        requirements = []
        requirement_indicators = [
            'must', 'should', 'need to', 'has to',
            'required', 'necessary', 'important'
        ]
        
        sentences = query.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in requirement_indicators):
                requirements.append(sentence.strip())
                
        return requirements

    def _extract_context_features(self, context: Dict) -> Dict[str, Any]:
        """Extract features from the context"""
        return {
            'domain': context.get('domain', 'general'),
            'style': context.get('style', 'standard'),
            'format': context.get('format', 'text'),
            'length': context.get('max_length', 1000),
            'tone': context.get('tone', 'neutral')
        }

    def _determine_content_type(self, query_features: Dict, context_features: Dict, 
                              learned_patterns: List[Dict]) -> ContentType:
        """Determine content type based on features and patterns"""
        if query_features['type'] == 'analysis':
            return ContentType.ANALYSIS
        elif query_features['type'] == 'generation':
            if context_features['domain'] == 'technical':
                return ContentType.TECHNICAL
            elif context_features['domain'] == 'educational':
                return ContentType.EDUCATIONAL
        elif query_features['complexity'] > 0.7:
            return ContentType.RESEARCH
            
        # Use learned patterns if available
        if learned_patterns:
            pattern_type = max(learned_patterns, 
                             key=lambda x: x.get('confidence', 0))['type']
            return ContentType[pattern_type]
            
        return ContentType.GENERAL

    def _get_relevant_patterns(self, query: str) -> List[Dict]:
        """Get relevant learned patterns for the query"""
        relevant = []
        for pattern_key, patterns in self.pattern_memory.items():
            if self._is_pattern_relevant(query, pattern_key):
                relevant.extend(patterns)
        return sorted(relevant, key=lambda x: x.get('confidence', 0), reverse=True)[:5]

    def _is_pattern_relevant(self, query: str, pattern_key: str) -> bool:
        """Check if a pattern is relevant to the query"""
        query_words = set(query.lower().split())
        pattern_words = set(pattern_key.lower().split())
        overlap = len(query_words & pattern_words)
        return overlap >= min(len(query_words), len(pattern_words)) * 0.3

    def _build_dynamic_prompt(self, query: str, strategy: ContentStrategy, context: Dict) -> str:
        """Build adaptive prompt based on strategy and context"""
        prompt_parts = [
            f"Generate content about: {query}\n",
            self._format_structure(strategy.structure),
            self._format_requirements(strategy.requirements),
            self._add_context_requirements(context),
            self._add_style_guide(strategy.style_guide)
        ]
        
        return "\n".join(prompt_parts)

    async def _process_content(self, content: str, strategy: ContentStrategy, context: Dict) -> str:
        """Process and enhance content with contextual awareness"""
        try:
            processed_content = content
            
            # Apply formatting rules
            processed_content = await self._apply_formatting(processed_content, strategy.formatting)
            
            # Add contextual enhancements
            if context.get('need_examples'):
                processed_content = await self._add_relevant_examples(processed_content, context)
                
            if context.get('need_references'):
                processed_content = await self._add_references(processed_content, context)
                
            # Add dynamic elements
            processed_content = await self._add_navigation_elements(processed_content, strategy)
            
            return processed_content
            
        except Exception as e:
            logger.error(f"Content processing failed: {str(e)}")
            return content

    async def _apply_formatting(self, content: str, formatting_rules: Dict) -> str:
        """Apply formatting rules asynchronously"""
        try:
            formatted_content = content
            
            # Apply each formatting rule
            for rule_type, rule in formatting_rules.items():
                formatted_content = await self._apply_format_rule(formatted_content, rule_type, rule)
                
            return formatted_content
            
        except Exception as e:
            logger.warning(f"Formatting failed: {str(e)}")
            return content

    async def _add_relevant_examples(self, content: str, context: Dict) -> str:
        """Add relevant examples asynchronously"""
        try:
            # Generate examples using the model
            prompt = f"""Generate relevant examples for the following content:
            {content[:500]}...
            
            Provide 2-3 concrete examples that illustrate the key points.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if response and response.text:
                return f"{content}\n\nExamples:\n{response.text}"
            return content
            
        except Exception as e:
            logger.warning(f"Adding examples failed: {str(e)}")
            return content

    async def _add_references(self, content: str, context: Dict) -> str:
        """Add references asynchronously"""
        try:
            # Generate references using the model
            prompt = f"""Generate relevant references for the following content:
            {content[:500]}...
            
            Provide 3-5 credible references that support the main points.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if response and response.text:
                return f"{content}\n\nReferences:\n{response.text}"
            return content
            
        except Exception as e:
            logger.warning(f"Adding references failed: {str(e)}")
            return content

    async def _add_navigation_elements(self, content: str, strategy: ContentStrategy) -> str:
        """Add navigation elements asynchronously"""
        try:
            # Add table of contents if content is long enough
            if len(content.split('\n')) > 10:
                toc = await self._generate_table_of_contents(content)
                content = f"{toc}\n\n{content}"
                
            return content
            
        except Exception as e:
            logger.warning(f"Adding navigation elements failed: {str(e)}")
            return content

    def _update_pattern_memory(self, query: str, content: str, content_type: ContentType) -> None:
        """Learn from successful content generation"""
        pattern = {
            'query': query,
            'type': content_type,
            'structure': self._extract_content_structure(content),
            'timestamp': datetime.now().isoformat()
        }
        
        if query[:50] not in self.pattern_memory:
            self.pattern_memory[query[:50]] = []
        self.pattern_memory[query[:50]].append(pattern)

    def _calculate_confidence(self, content: str, strategy: ContentStrategy) -> float:
        """Calculate confidence score for generated content"""
        scores = []
        
        # Check structure compliance
        structure_score = self._check_structure_compliance(content, strategy.structure)
        scores.append(structure_score)
        
        # Check requirements fulfillment
        req_score = self._check_requirements_fulfillment(content, strategy.requirements)
        scores.append(req_score)
        
        # Check formatting quality
        format_score = self._check_formatting_quality(content, strategy.formatting)
        scores.append(format_score)
        
        return sum(scores) / len(scores)

    # ...existing helper methods...
