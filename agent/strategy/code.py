from typing import List, Dict, Any, Optional
from .base import Strategy, StrategyResult
import re
import ast
from dataclasses import dataclass, field
from functools import lru_cache
from tools.code_tools import CodeGeneratorTool as CodeGenerator, CodeAnalysisTool as CodeAnalyzer, AdaptiveAlgorithmRegistry, AdaptiveCodeAnalyzer as FlexibleCodeAnalyzer
import time

@dataclass
class StrategyContext:
    """Dynamic context for strategy execution"""
    task_type: str
    requirements: Dict[str, Any]
    constraints: List[str] = field(default_factory=list)
    adaptations: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    feedback_metrics: Dict[str, float] = field(default_factory=dict)
    adaptation_rules: Dict[str, Any] = field(default_factory=dict)

class AdaptiveCodeStrategy(Strategy):
    """Enhanced code strategy with dynamic adaptation"""
    def __init__(self):
        super().__init__()
        self.pattern_registry = AdaptiveAlgorithmRegistry()
        self.analyzer = FlexibleCodeAnalyzer()
        self.strategy_cache = {}
        self.adaptation_engine = self._create_adaptation_engine()
        self.learning_rate = 0.1

    def _create_adaptation_engine(self) -> Dict[str, Any]:
        return {
            'patterns': {},
            'rules': {},
            'feedback': [],
            'meta_templates': self._load_meta_templates()
        }

    @lru_cache(maxsize=100)
    def _load_meta_templates(self) -> Dict[str, Any]:
        return {
            'code_patterns': self._generate_dynamic_patterns(),
            'adaptation_rules': self._generate_adaptation_rules()
        }
        
    async def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        try:
            strategy_context = self._build_strategy_context(task, context)
            
            # Dynamic strategy selection
            selected_strategy = self._select_optimal_strategy(task, strategy_context)
            
            # Adaptive pattern matching
            pattern = await self._find_or_create_pattern(task, strategy_context)
            
            # Generate and analyze code with feedback loop
            code_result = await self._generate_adaptive_code(pattern, strategy_context)
            analysis = await self._analyze_with_feedback(code_result, strategy_context)
            
            # Meta-programming adaptation
            if analysis['requires_adaptation']:
                code_result = await self._adapt_code_dynamically(code_result, analysis)
            
            # Update learning metrics
            self._update_learning_metrics(pattern, code_result, analysis)
            
            return StrategyResult(
                success=True,
                output={
                    'code': code_result['code'],
                    'analysis': analysis,
                    'pattern_used': pattern['metadata'],
                    'adaptations': code_result.get('adaptations', []),
                    'confidence': self._calculate_confidence(analysis)
                }
            )
            
        except Exception as e:
            self._handle_execution_error(e, strategy_context)
            return StrategyResult(success=False, error=str(e))

    async def _find_or_create_pattern(self, task: str, context: StrategyContext) -> Dict[str, Any]:
        pattern = self.pattern_registry.find_best_pattern(task, context)
        if not pattern or pattern['confidence'] < 0.7:
            pattern = await self._create_adaptive_pattern(task, context)
        return pattern

    async def _adapt_code_dynamically(self, code_result: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        adaptations = []
        if analysis['complexity'] > 0.7:
            adaptations.append(self._optimize_complexity(code_result['code']))
        if analysis['maintainability'] < 0.6:
            adaptations.append(self._improve_maintainability(code_result['code']))
            
        code_result['code'] = self._apply_adaptations(code_result['code'], adaptations)
        code_result['adaptations'] = adaptations
        return code_result

    def _update_learning_metrics(self, pattern: Dict[str, Any], result: Dict[str, Any], analysis: Dict[str, Any]):
        """Enhanced learning from execution results"""
        metrics = {
            'success_rate': 1.0 if result.get('success') else 0.0,
            'complexity_score': analysis.get('complexity', 0.5),
            'adaptation_effectiveness': self._calculate_adaptation_effectiveness(result),
            'pattern_relevance': self._calculate_pattern_relevance(pattern, result)
        }
        
        # Update pattern weights
        self.pattern_registry.update_pattern_weights(pattern['id'], metrics)
        
        # Store learning history
        self.strategy_cache[pattern['id']] = {
            'metrics': metrics,
            'timestamp': time.time()
        }

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        weights = {
            'complexity': 0.3,
            'maintainability': 0.3,
            'security': 0.2,
            'performance': 0.2
        }
        return sum(analysis.get(k, 0) * w for k, w in weights.items())

    def _build_strategy_context(self, task: str, context: Dict[str, Any]) -> StrategyContext:
        """Build dynamic strategy context"""
        requirements = self._analyze_requirements(task)
        return StrategyContext(
            task_type=self._detect_task_type(task),
            requirements=requirements,
            constraints=context.get('constraints', []),
            adaptations=self.strategy_cache.get(task[:50], [])
        )

    def _learn_from_execution(self, pattern: Dict[str, Any], result: Dict[str, Any], analysis: Dict[str, Any]):
        """Learn from strategy execution"""
        success = result.get('success', False) and analysis['confidence'] > 0.7
        self.pattern_registry.learn_from_execution(pattern, success, {
            'analysis': analysis,
            'result': result
        })

class CodeStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.code_patterns = {
            'function': r'(?:create|write|implement)\s+(?:a|an|the)?\s*function',
            'class': r'(?:create|write|implement)\s+(?:a|an|the)?\s*class',
            'algorithm': r'(?:implement|create)\s+(?:a|an|the)?\s*algorithm',
            'script': r'(?:write|create)\s+(?:a|an|the)?\s*script'
        }
        
        # Code quality metrics
        self.quality_checks = {
            'complexity': self._check_complexity,
            'maintainability': self._check_maintainability,
            'security': self._check_security,
            'performance': self._check_performance
        }
        
        # Test generation templates
        self.test_templates = {
            'unit_test': "def test_{func_name}():\n    assert {func_name}({inputs}) == {expected}",
            'edge_case': "def test_{func_name}_edge_case():\n    assert {func_name}({edge_case}) == {expected}"
        }

    async def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        try:
            # Analyze requirements
            requirements = self._analyze_code_requirements(task)
            
            # Generate initial code
            code_result = await self._generate_code(task, requirements, context)
            if not code_result.get('success'):
                return StrategyResult(success=False, error=code_result.get('error'))
            
            # Analyze and improve code
            analyzed_code = self._analyze_code(code_result['code'])
            improved_code = self._improve_code(analyzed_code)
            
            # Generate tests
            tests = self._generate_tests(improved_code, requirements)
            
            # Validate implementation
            validation_result = self._validate_implementation(improved_code, tests)
            
            return StrategyResult(
                success=True,
                output={
                    'code': improved_code,
                    'tests': tests,
                    'analysis': analyzed_code,
                    'validation': validation_result,
                    'type': 'code_implementation'
                },
                confidence=validation_result.get('confidence', 0.8)
            )
            
        except Exception as e:
            return StrategyResult(success=False, error=str(e))

    def _analyze_code_requirements(self, task: str) -> Dict[str, Any]:
        """Extract detailed code requirements from task"""
        requirements = {
            'type': self._detect_code_type(task),
            'complexity': self._estimate_complexity(task),
            'constraints': self._extract_constraints(task),
            'expected_features': self._extract_features(task)
        }
        
        return requirements

    def _detect_code_type(self, task: str) -> str:
        """Detect type of code implementation needed"""
        task_lower = task.lower()
        for code_type, pattern in self.code_patterns.items():
            if re.search(pattern, task_lower):
                return code_type
        return 'function'  # default type

    async def _generate_code(self, task: str, requirements: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code with context awareness"""
        try:
            # Prepare generation context
            generation_context = {
                'task': task,
                'requirements': requirements,
                'style_guide': context.get('style_guide', 'pep8'),
                'language': context.get('language', 'python'),
                'frameworks': context.get('frameworks', [])
            }
            
            # Generate code using code generator tool
            code_result = await context['tools']['code_generator'].execute(
                query=task,
                params=generation_context
            )
            
            return code_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code quality and structure"""
        analysis = {}
        
        try:
            # Parse and analyze AST
            tree = ast.parse(code)
            
            # Collect metrics
            analysis['complexity'] = self._calculate_complexity(tree)
            analysis['maintainability'] = self._analyze_maintainability(tree)
            analysis['security_issues'] = self._check_security_issues(tree)
            analysis['performance_hints'] = self._analyze_performance(tree)
            
            # Run quality checks
            analysis['quality_scores'] = {
                check: func(code, tree) 
                for check, func in self.quality_checks.items()
            }
            
        except Exception as e:
            analysis['error'] = str(e)
            
        return analysis

    def _generate_tests(self, code: str, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive test suite"""
        tests = []
        
        try:
            # Parse code to extract testable elements
            tree = ast.parse(code)
            
            # Generate unit tests
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    tests.extend(self._generate_function_tests(node))
                elif isinstance(node, ast.ClassDef):
                    tests.extend(self._generate_class_tests(node))
                    
            # Add edge case tests
            tests.extend(self._generate_edge_case_tests(requirements))
            
        except Exception as e:
            tests.append({
                'type': 'error',
                'message': str(e)
            })
            
        return tests

    def _validate_implementation(self, code: str, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate code implementation against requirements"""
        validation = {
            'passed_tests': 0,
            'total_tests': len(tests),
            'issues': [],
            'confidence': 0.0
        }
        
        try:
            # Create isolated environment for testing
            namespace = {}
            exec(code, namespace)
            
            # Run tests
            for test in tests:
                try:
                    exec(test['code'], namespace)
                    validation['passed_tests'] += 1
                except Exception as e:
                    validation['issues'].append({
                        'test': test['name'],
                        'error': str(e)
                    })
            
            # Calculate confidence based on test results and code quality
            validation['confidence'] = (
                validation['passed_tests'] / validation['total_tests']
                if validation['total_tests'] > 0 else 0.5
            )
            
        except Exception as e:
            validation['issues'].append({
                'type': 'execution_error',
                'error': str(e)
            })
            
        return validation
