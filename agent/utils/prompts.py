from typing import Dict, Any, List
from string import Template
from dataclasses import dataclass
from enum import Enum

class ContentStyle(Enum):
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    INFORMAL = "informal"
    JOURNALISTIC = "journalistic"
    NARRATIVE = "narrative"

@dataclass
class PromptTemplate:
    template: str
    required_vars: set[str]
    
    def format(self, **kwargs) -> str:
        missing = self.required_vars - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        return Template(self.template).safe_substitute(**kwargs)

class PromptLibrary:
    SYSTEM_PROMPT = PromptTemplate(
        template="""You are an AI research assistant with access to the following tools:

$tool_descriptions

To use a tool, respond with a JSON object with the following structure:
{
    "thought": "Your reasoning about what to do next",
    "tool": "tool_name",
    "input": "input for the tool"
}

If you have gathered enough information to answer the question, respond with:
{
    "thought": "Your final reasoning",
    "answer": "Your final answer",
    "confidence": 0.0-1.0
}

Additional context:
$context

Remember to:
1. Break down complex tasks into steps
2. Verify information from multiple sources
3. Provide detailed reasoning for your conclusions""",
        required_vars={'tool_descriptions', 'context'}
    )
    
    RESEARCH_PROMPT = PromptTemplate(
        template="""Task: $task

Previous findings: $findings

Focus on:
- Verifying information accuracy
- Cross-referencing multiple sources
- Identifying key insights
- Ensuring comprehensive coverage

What should be the next step?""",
        required_vars={'task', 'findings'}
    )
    
    CODE_GENERATION_PROMPT = PromptTemplate(
        template="""Task: $task

Requirements:
- Language: $language
- Performance considerations: $performance_reqs
- Security requirements: $security_reqs

Previous code analysis:
$previous_analysis

Generate code that is:
1. Well-documented
2. Efficient
3. Secure
4. Maintainable""",
        required_vars={'task', 'language', 'performance_reqs', 
                      'security_reqs', 'previous_analysis'}
    )
    
    ANALYSIS_PROMPT = PromptTemplate(
        template="""Analyze the following results:
$results

Consider:
- Accuracy of information
- Completeness of coverage
- Potential biases
- Areas needing further investigation

Task context:
$task_context""",
        required_vars={'results', 'task_context'}
    )

    CONTENT_PROMPT = PromptTemplate(
        template="""Task: $task

Style: $style
Target Audience: $audience
Tone: $tone
Length: $length
Key Points:
$key_points

Additional Requirements:
- Citations: $citations_required
- Examples: $include_examples
- Technical depth: $technical_depth

Previous context:
$context

Generate content that:
1. Matches the specified style and tone
2. Engages the target audience
3. Covers all key points thoroughly
4. Maintains coherent structure
5. Uses appropriate language and terminology""",
        required_vars={'task', 'style', 'audience', 'tone', 'length', 
                      'key_points', 'citations_required', 'include_examples', 
                      'technical_depth', 'context'}
    )

    GENERAL_QUERY_PROMPT = PromptTemplate(
        template="""Query: $query

Context: $context

Think step by step:
1. Understand the query type and requirements
2. Consider relevant context and background
3. Formulate a clear and concise response
4. Validate accuracy and completeness
5. Provide additional context if helpful

Response should be:
- Accurate and well-reasoned
- Appropriate to the query context
- Clear and understandable
- Properly structured""",
        required_vars={'query', 'context'}
    )

    CHAIN_OF_THOUGHT_PROMPT = PromptTemplate(
        template="""Task: $task

Let's approach this step by step:

1. Initial Understanding:
   - What are we trying to achieve?
   - What context do we have?

2. Analysis:
   - Break down the requirements
   - Identify key components
   - Consider constraints

3. Strategy:
   - Determine best approach
   - Plan the steps
   - Consider alternatives

4. Implementation:
   - Execute the plan
   - Monitor progress
   - Adjust as needed

5. Validation:
   - Verify results
   - Check against requirements
   - Consider improvements

Context: $context
Previous steps: $previous_steps""",
        required_vars={'task', 'context', 'previous_steps'}
    )

class PromptManager:
    def __init__(self):
        self.library = PromptLibrary()
        self.context_history: Dict[str, Any] = {}
        self.style_templates = {
            ContentStyle.ACADEMIC: {
                'tone': 'formal',
                'structure': 'systematic',
                'citations': True
            },
            ContentStyle.TECHNICAL: {
                'tone': 'precise',
                'structure': 'detailed',
                'examples': True
            },
            ContentStyle.INFORMAL: {
                'tone': 'conversational',
                'structure': 'flexible',
                'examples': True
            }
        }
        
    def get_system_prompt(self, tools: Dict[str, Any], 
                         context: str = "") -> str:
        """Get formatted system prompt"""
        tool_descriptions = "\n".join(
            f"- {name}: {tool.get_description()}" 
            for name, tool in tools.items()
        )
        return self.library.SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            context=context
        )
    
    def get_research_prompt(self, task: str, findings: str = "") -> str:
        """Get research-focused prompt"""
        return self.library.RESEARCH_PROMPT.format(
            task=task,
            findings=findings or "No previous findings."
        )
    
    def get_code_prompt(self, task: str, language: str,
                       perf_reqs: str = "Optimize for readability",
                       security_reqs: str = "Standard security practices",
                       analysis: str = "") -> str:
        """Get code generation prompt"""
        return self.library.CODE_GENERATION_PROMPT.format(
            task=task,
            language=language,
            performance_reqs=perf_reqs,
            security_reqs=security_reqs,
            previous_analysis=analysis or "No previous analysis."
        )
    
    def get_analysis_prompt(self, results: str, 
                          task_context: str = "") -> str:
        """Get analysis prompt"""
        return self.library.ANALYSIS_PROMPT.format(
            results=results,
            task_context=task_context or "No specific context provided."
        )

    def get_content_prompt(self, 
                          task: str,
                          style: ContentStyle = ContentStyle.INFORMAL,
                          audience: str = "general",
                          length: str = "medium",
                          key_points: List[str] = None) -> str:
        """Get content generation prompt with style customization"""
        style_config = self.style_templates.get(style, self.style_templates[ContentStyle.INFORMAL])
        
        return self.library.CONTENT_PROMPT.format(
            task=task,
            style=style.value,
            audience=audience,
            tone=style_config['tone'],
            length=length,
            key_points="\n".join(f"- {point}" for point in (key_points or [])),
            citations_required=str(style_config.get('citations', False)),
            include_examples=str(style_config.get('examples', False)),
            technical_depth=style_config.get('structure', 'balanced'),
            context=self.context_history.get(task, "No previous context")
        )

    def get_chain_of_thought_prompt(self, task: str, previous_steps: List[str] = None) -> str:
        """Get chain-of-thought prompt for complex reasoning"""
        return self.library.CHAIN_OF_THOUGHT_PROMPT.format(
            task=task,
            context=self.context_history.get(task, "No previous context"),
            previous_steps="\n".join(f"- {step}" for step in (previous_steps or []))
        )

    def get_general_query_prompt(self, query: str) -> str:
        """Get general query prompt with context awareness"""
        return self.library.GENERAL_QUERY_PROMPT.format(
            query=query,
            context=self.context_history.get(query, "No specific context")
        )
