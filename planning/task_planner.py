from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from datetime import datetime
import networkx as nx

class TaskType(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CODE = "code"
    DATA = "data"
    COMPOSITE = "composite"

@dataclass
class PlanStep:
    id: str
    tool: str
    params: Dict
    dependencies: List[str]
    estimated_time: float
    priority: int

@dataclass
class TaskPlan:
    steps: List[PlanStep]
    estimated_time: float
    metadata: Dict[str, Any]

class TaskPlanner:
    def __init__(self, available_tools: List[str]):
        self.available_tools = available_tools
        self.execution_history = []
        self.tool_performance = {}
        self._initialize_nltk()

    def _initialize_nltk(self):
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download(['punkt', 'averaged_perceptron_tagger'], quiet=True)

    def create_plan(self, task: str, context: Optional[Dict] = None) -> TaskPlan:
        """Create an optimized execution plan"""
        # Analyze task requirements
        requirements = self._analyze_requirements(task)
        
        # Build dependency graph
        graph = self._build_dependency_graph(requirements)
        
        # Optimize step ordering
        ordered_steps = self._optimize_step_order(graph)
        
        # Assign tools and parameters
        steps = self._assign_tools(ordered_steps, context)
        
        # Calculate estimated completion time
        total_time = sum(step.estimated_time for step in steps)
        
        return TaskPlan(
            steps=steps,
            estimated_time=total_time,
            metadata={
                'task_type': self._analyze_task_type(task),
                'complexity': len(steps),
                'created_at': datetime.now()
            }
        )

    def _analyze_task_type(self, task: str) -> TaskType:
        """Determine the type of task using NLP analysis"""
        tokens = word_tokenize(task.lower())
        pos_tags = pos_tag(tokens)
        
        # Look for specific indicators in the task
        if any(word in tokens for word in ['code', 'implement', 'program', 'function']):
            return TaskType.CODE
        elif any(word in tokens for word in ['analyze', 'calculate', 'compare']):
            return TaskType.ANALYSIS
        elif any(word in tokens for word in ['data', 'dataset', 'database']):
            return TaskType.DATA
        elif len([tag for _, tag in pos_tags if tag.startswith('VB')]) > 2:
            return TaskType.COMPOSITE
        else:
            return TaskType.RESEARCH

    def _decompose_task(self, task: str, task_type: TaskType) -> List[str]:
        """Break down complex tasks into subtasks"""
        if task_type == TaskType.COMPOSITE:
            # Use sentence tokenization for complex tasks
            return [sent.strip() for sent in nltk.sent_tokenize(task)]
        return [task]  # Return single task if not composite

    def _create_step(
        self, 
        step_id: str, 
        subtask: str, 
        task_type: TaskType,
        context: Optional[Dict]
    ) -> PlanStep:
        """Create a detailed plan step for a subtask"""
        tool = self._select_tool(subtask, task_type)
        
        return PlanStep(
            id=step_id,
            type=task_type,
            description=subtask,
            tool=tool,
            params=self._generate_tool_params(subtask, tool, context),
            estimated_time=self._estimate_step_time(subtask, tool),
            confidence=self._calculate_step_confidence(subtask, tool)
        )

    def _select_tool(self, subtask: str, task_type: TaskType) -> str:
        """Select the most appropriate tool for the task"""
        tool_mapping = {
            TaskType.RESEARCH: ["google_search", "web_scraper"],
            TaskType.CODE: ["code_generator", "code_analysis"],
            TaskType.DATA: ["dataset", "data_analysis"],
            TaskType.ANALYSIS: ["analysis_tool", "data_analysis"]
        }
        
        preferred_tools = tool_mapping.get(task_type, ["google_search"])
        for tool in preferred_tools:
            if tool in self.available_tools:
                return tool
                
        return self.available_tools[0]  # Default to first available tool

    def _generate_tool_params(self, subtask: str, tool: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Generate parameters for tool execution"""
        base_params = {"query": subtask}
        
        if context:
            base_params.update({
                "context": context,
                "constraints": context.get("constraints", {}),
                "preferences": context.get("preferences", {})
            })
            
        return base_params

    def _add_step_dependencies(self, steps: List[PlanStep]):
        """Add dependencies between steps based on their relationships"""
        for i, step in enumerate(steps[1:], 1):
            if step.type in [TaskType.ANALYSIS, TaskType.CODE]:
                # These steps might depend on previous research
                research_steps = [s.id for s in steps[:i] if s.type == TaskType.RESEARCH]
                if research_steps:
                    step.dependencies = research_steps

    def _calculate_complexity(self, task: str) -> float:
        """Calculate task complexity score"""
        tokens = word_tokenize(task)
        pos_tags = pos_tag(tokens)
        
        # Complexity factors
        num_verbs = len([tag for _, tag in pos_tags if tag.startswith('VB')])
        num_nouns = len([tag for _, tag in pos_tags if tag.startswith('NN')])
        sentence_length = len(tokens)
        
        return min(1.0, (num_verbs * 0.2 + num_nouns * 0.1 + sentence_length * 0.01))

    def _estimate_step_time(self, subtask: str, tool: str) -> float:
        """Estimate execution time for a step"""
        base_times = {
            "google_search": 10.0,
            "web_scraper": 20.0,
            "code_generator": 30.0,
            "code_analysis": 15.0,
            "dataset": 25.0,
            "data_analysis": 20.0
        }
        
        base_time = base_times.get(tool, 15.0)
        complexity_factor = self._calculate_complexity(subtask)
        
        return base_time * (1 + complexity_factor)

    def _calculate_step_confidence(self, subtask: str, tool: str) -> float:
        """Calculate confidence score for a step"""
        # Base confidence by tool
        tool_confidence = {
            "google_search": 0.9,
            "web_scraper": 0.8,
            "code_generator": 0.7,
            "code_analysis": 0.85,
            "dataset": 0.75,
            "data_analysis": 0.8
        }
        
        base_confidence = tool_confidence.get(tool, 0.7)
        complexity_penalty = self._calculate_complexity(subtask) * 0.2
        
        return max(0.1, base_confidence - complexity_penalty)

    def _get_required_tools(self, steps: List[PlanStep]) -> List[str]:
        """Get list of unique tools required for the plan"""
        return list(set(step.tool for step in steps))

    def _optimize_step_order(self, graph: nx.DiGraph) -> List[str]:
        """Optimize step ordering using topological sort and historical performance"""
        # Get basic topological order
        basic_order = list(nx.topological_sort(graph))
        
        # Consider tool performance history
        weighted_order = []
        for step in basic_order:
            tool = graph.nodes[step].get('tool')
            if tool in self.tool_performance:
                weight = self.tool_performance[tool].get('success_rate', 0.5)
                weighted_order.append((step, weight))
            else:
                weighted_order.append((step, 0.5))
                
        # Sort by weight while preserving dependencies
        return self._weighted_topological_sort(graph, weighted_order)
        
    def update_tool_performance(self, tool: str, execution_time: float, success: bool):
        """Track tool performance for future optimization"""
        if tool not in self.tool_performance:
            self.tool_performance[tool] = {
                'executions': 0,
                'successes': 0,
                'avg_time': 0.0
            }
            
        stats = self.tool_performance[tool]
        stats['executions'] += 1
        if success:
            stats['successes'] += 1
        stats['avg_time'] = (stats['avg_time'] * (stats['executions'] - 1) + execution_time) / stats['executions']
        stats['success_rate'] = stats['successes'] / stats['executions']
