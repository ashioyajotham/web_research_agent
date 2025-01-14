from typing import List, Dict, Any
from .base import Strategy, StrategyResult
import re
import ast

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
