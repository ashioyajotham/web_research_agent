from dataclasses import dataclass, field
import asyncio
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
    CRITERIA_SEARCH = "criteria_search"

@dataclass
class PlanStep:
    id: str
    task: str
    tool: str
    params: Dict[str, Any]
    dependencies: List[str]
    type: TaskType
    estimated_time: float
    complexity: float

@dataclass
class PlanMetrics:
    estimated_time: float
    confidence: float
    cost: float
    benefit: float
    complexity: float

@dataclass
class TaskPlan:
    steps: List[PlanStep]
    type: TaskType
    dependencies: nx.DiGraph
    estimated_duration: float
    total_complexity: float
    parallel_execution: bool

@dataclass
class TaskConfiguration:
    """Dynamic configuration for task planning"""
    tool_weights: Dict[str, float] = field(default_factory=dict)
    complexity_factors: Dict[str, float] = field(default_factory=dict)
    parallel_threshold: float = 0.7
    replan_threshold: float = 0.5
    max_parallel_steps: int = 3
    learning_rate: float = 0.1

class TaskPlanner:
    def __init__(self, available_tools: List[str], config: Optional[TaskConfiguration] = None):
        self.tools = available_tools
        self.dependency_graph = nx.DiGraph()
        self._initialize_nltk()
        
        # Use configurable settings
        self.config = config or TaskConfiguration()
        
        # Add learning and adaptation capabilities
        self.tool_performance = {}
        self.task_patterns = {}
        self.failed_patterns = set()
        
        # Historical performance tracking
        self.execution_history = []
        self.pattern_success_rates = {}

    def _initialize_nltk(self):
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download(['punkt', 'averaged_perceptron_tagger'], quiet=True)

    async def create_plan(self, task: str, context: Optional[Dict] = None) -> TaskPlan:
        """Create execution plan for task"""
        task_type = self._analyze_task_type(task)
        subtasks = self._decompose_task(task, task_type)
        
        steps = []
        for i, subtask in enumerate(subtasks):
            step = self._create_step(
                f"step_{i}",
                subtask,
                task_type,
                context
            )
            steps.append(step)
            
        self._add_step_dependencies(steps)
        complexity = self._calculate_complexity(task)
        
        return TaskPlan(
            steps=steps,
            type=task_type,
            dependencies=self.dependency_graph,
            estimated_duration=len(steps) * 2.0,
            total_complexity=complexity,
            parallel_execution=self._can_parallelize(steps)
        )

    def _analyze_task_type(self, task: str) -> TaskType:
        """Determine task type using NLP and historical patterns"""
        tokens = word_tokenize(task.lower())
        pos_tags = pos_tag(tokens)
        
        # Check historical patterns first
        task_pattern = self._extract_task_pattern(tokens)
        if task_pattern in self.task_patterns:
            return self.task_patterns[task_pattern]
            
        # Use NLP-based analysis with learned weights
        type_scores = {t: 0.0 for t in TaskType}
        
        for word in tokens:
            for task_type in TaskType:
                if word in self.config.tool_weights.get(task_type, {}):
                    type_scores[task_type] += self.config.tool_weights[task_type][word]
        
        # Get highest scoring type
        best_type = max(type_scores.items(), key=lambda x: x[1])[0]
        
        # Store pattern for future use
        self.task_patterns[task_pattern] = best_type
        return best_type

    def _extract_task_pattern(self, tokens: List[str]) -> str:
        """Extract key pattern from task tokens"""
        return " ".join(sorted([t for t in tokens if t not in set(['the', 'a', 'an', 'in', 'on', 'at'])]))

    def _decompose_task(self, task: str, task_type: TaskType) -> List[str]:
        """Break down complex task into subtasks"""
        if task_type == TaskType.COMPOSITE:
            return self._decompose_composite(task)
        return [task]

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
            task=subtask,
            type=task_type,
            tool=tool,
            params=self._generate_tool_params(subtask, tool, context),
            estimated_time=self._estimate_step_time(subtask, tool),
            complexity=self._calculate_complexity(subtask)
        )

    def _select_tool(self, subtask: str, task_type: TaskType) -> str:
        """Select tool based on performance history and context"""
        available_tools = set(self.tools)
        
        # Check historical performance
        if subtask in self.tool_performance:
            best_tool = max(
                self.tool_performance[subtask].items(),
                key=lambda x: x[1]['success_rate']
            )[0]
            if best_tool in available_tools:
                return best_tool
        
        # Use learned tool weights
        tool_scores = {tool: 0.0 for tool in available_tools}
        for tool in available_tools:
            # Base score from configuration
            tool_scores[tool] = self.config.tool_weights.get(tool, {}).get(task_type.value, 0.5)
            
            # Adjust based on historical success
            if tool in self.pattern_success_rates:
                tool_scores[tool] *= (1 + self.pattern_success_rates[tool])
                
        return max(tool_scores.items(), key=lambda x: x[1])[0]

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

    def _optimize_parallel_execution(self, steps: List[PlanStep]) -> List[PlanStep]:
        """Optimize steps for parallel execution"""
        parallel_groups = []
        current_group = []
        
        for step in steps:
            if len(current_group) < self.config.max_parallel_steps and self._can_run_parallel(step, current_group):
                current_group.append(step)
            else:
                if current_group:
                    parallel_groups.append(current_group)
                current_group = [step]
                
        if current_group:
            parallel_groups.append(current_group)
            
        # Flatten and maintain dependencies
        optimized_steps = []
        for group in parallel_groups:
            for step in group:
                step.parallel_group = id(group)
                optimized_steps.append(step)
                
        return optimized_steps

    def _calculate_plan_metrics(self, steps: List[PlanStep], context: Optional[Dict]) -> PlanMetrics:
        """Calculate comprehensive plan metrics"""
        total_time = sum(step.estimated_time for step in steps)
        confidence = self._calculate_plan_confidence(steps)
        cost = self._calculate_plan_cost(steps)
        benefit = self._estimate_plan_benefit(steps, context)
        complexity = self._calculate_plan_complexity(steps)
        
        return PlanMetrics(
            estimated_time=total_time,
            confidence=confidence,
            cost=cost,
            benefit=benefit,
            complexity=complexity
        )

    def _generate_fallback_steps(self, task: str) -> List[PlanStep]:
        """Generate fallback steps for recovery"""
        fallback_steps = []
        task_type = self._analyze_task_type(task)
        
        # Add general fallback based on task type
        if task_type == TaskType.RESEARCH:
            fallback_steps.append(PlanStep(
                id="fallback_search",
                task=task,
                tool="google_search",
                params={"query": task, "fallback": True},
                dependencies=[],
                type=task_type,
                estimated_time=10.0,
                complexity=self._calculate_complexity(task)
            ))
            
        return fallback_steps

    async def replan_on_failure(self, failed_step: PlanStep, context: Dict) -> Optional[List[PlanStep]]:
        """Dynamically replan on step failure"""
        self.failed_patterns.add((failed_step.tool, failed_step.id))
        
        # Try alternative approach based on failure
        alternative_steps = []
        
        # Add step-specific alternatives
        if failed_step.tool == "google_search":
            alternative_steps.append(PlanStep(
                id=f"alternative_{failed_step.id}",
                task=failed_step.task,
                tool="web_scraper",
                params=failed_step.params,
                dependencies=failed_step.dependencies,
                type=failed_step.type,
                estimated_time=failed_step.estimated_time * 1.5,
                complexity=failed_step.complexity
            ))
            
        return alternative_steps if alternative_steps else None

    def _can_run_parallel(self, step: PlanStep, group: List[PlanStep]) -> bool:
        """Determine if step can run in parallel with group"""
        # Check dependencies
        if any(dep in [s.id for s in group] for dep in step.dependencies):
            return False
            
        # Check resource conflicts
        if any(s.tool == step.tool for s in group):
            return False
            
        # Check confidence threshold
        return self._calculate_step_confidence(step) >= self.config.parallel_threshold

    def learn_from_execution(self, 
                           step: PlanStep, 
                           success: bool, 
                           execution_time: float, 
                           results: Any):
        """Learn from execution results"""
        # Update tool performance
        if step.task not in self.tool_performance:
            self.tool_performance[step.task] = {}
        
        if step.tool not in self.tool_performance[step.task]:
            self.tool_performance[step.task][step.tool] = {
                'success_rate': 1.0,
                'avg_time': execution_time,
                'executions': 1
            }
        else:
            stats = self.tool_performance[step.task][step.tool]
            stats['executions'] += 1
            stats['success_rate'] = (stats['success_rate'] * (stats['executions'] - 1) + float(success)) / stats['executions']
            stats['avg_time'] = (stats['avg_time'] * (stats['executions'] - 1) + execution_time) / stats['executions']

        # Update pattern success rates
        pattern = self._extract_task_pattern(word_tokenize(step.task))
        if pattern not in self.pattern_success_rates:
            self.pattern_success_rates[pattern] = 0.0
        
        # Apply learning rate to update
        current_rate = self.pattern_success_rates[pattern]
        self.pattern_success_rates[pattern] = current_rate + self.config.learning_rate * (float(success) - current_rate)

        # Store execution record
        self.execution_history.append({
            'step': step,
            'success': success,
            'time': execution_time,
            'results': results
        })

    def _optimize_plan(self, steps: List[PlanStep]) -> List[PlanStep]:
        """Optimize plan based on learned patterns"""
        optimized_steps = []
        
        # Group steps by patterns
        pattern_groups = self._group_by_patterns(steps)
        
        # Reorder based on success patterns
        for group in pattern_groups:
            if len(group) > 1:
                group.sort(
                    key=lambda s: self.pattern_success_rates.get(
                        self._extract_task_pattern(word_tokenize(s.task)), 0.5
                    ),
                    reverse=True
                )
            optimized_steps.extend(group)
            
        return optimized_steps

    def _group_by_patterns(self, steps: List[PlanStep]) -> List[List[PlanStep]]:
        """Group steps by similar patterns"""
        patterns = {}
        for step in steps:
            pattern = self._extract_task_pattern(word_tokenize(step.task))
            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(step)
            
        return list(patterns.values())
