from typing import Dict, Any
from string import Template
from dataclasses import dataclass

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

class PromptManager:
    def __init__(self):
        self.library = PromptLibrary()
        self.context_history: Dict[str, Any] = {}
        
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
