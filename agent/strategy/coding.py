from typing import List, Dict, Any
import re
from .base import Strategy, StrategyResult

class CodingStrategy(Strategy):
    def __init__(self):
        # Expand coding patterns recognition
        self.coding_patterns = {
            'implementation': {
                'keywords': ["implement", "create", "write", "develop", "build"],
                'confidence': 0.8
            },
            'algorithm': {
                'keywords': ["algorithm", "function", "method", "solution"],
                'confidence': 0.7
            },
            'data_structure': {
                'keywords': ["tree", "graph", "list", "stack", "queue", "heap"],
                'confidence': 0.9
            }
        }

        # Add code style guides
        self.style_guides = {
            'python': {
                'pep8': True,
                'type_hints': True,
                'docstrings': True
            },
            'javascript': {
                'eslint': True,
                'typescript': False
            }
        }

        # Add test requirements
        self.test_requirements = {
            'unit_tests': True,
            'example_usage': True,
            'edge_cases': True
        }

        # Keep existing language patterns
        self.language_patterns = {
            "python": r"python|django|flask",
            "javascript": r"javascript|react|node|js",
            "typescript": r"typescript|angular|ts",
            "go": r"golang|go lang|go program"
        }

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        
        # Calculate pattern match scores
        pattern_scores = []
        for category, info in self.coding_patterns.items():
            matches = sum(1 for kw in info['keywords'] if kw in task_lower)
            if matches:
                pattern_scores.append(matches * info['confidence'])

        # Language detection score
        language_score = 0.3 if any(
            re.search(pattern, task_lower) 
            for pattern in self.language_patterns.values()
        ) else 0

        # Calculate final confidence
        if pattern_scores:
            return min(max(pattern_scores) + language_score, 1.0)
        return 0.0

    def get_required_tools(self) -> List[str]:
        return ["code_analysis", "google_search"]

    async def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        try:
            # Step 1: Analyze requirements
            requirements = self._analyze_requirements(task)
            
            # Step 2: Plan implementation steps
            implementation_plan = self._create_implementation_plan(requirements)
            
            # Step 3: Generate code with proper structure
            code_result = await self._generate_code(
                task, 
                implementation_plan,
                context.get('tools', {})
            )
            
            # Step 4: Add tests and examples
            code_with_tests = self._add_tests_and_examples(
                code_result['code'],
                requirements
            )
            
            # Step 5: Quality checks
            quality_report = self._check_code_quality(code_with_tests)
            
            return StrategyResult(
                success=True,
                output={
                    "code": code_with_tests,
                    "explanation": code_result.get('explanation', ''),
                    "implementation_steps": implementation_plan,
                    "quality_report": quality_report,
                    "test_coverage": self._calculate_test_coverage(code_with_tests)
                },
                confidence=self._calculate_confidence(quality_report),
                metadata={
                    "language": requirements['language'],
                    "complexity": quality_report['complexity'],
                    "has_tests": bool(quality_report['test_count'])
                }
            )

        except Exception as e:
            return StrategyResult(
                success=False,
                error=str(e)
            )

    def _analyze_requirements(self, task: str) -> Dict[str, Any]:
        """Extract detailed requirements from task"""
        requirements = {
            'language': self._detect_language(task),
            'complexity': self._estimate_complexity(task),
            'features': self._extract_features(task),
            'constraints': self._extract_constraints(task),
            'test_requirements': self.test_requirements.copy()
        }
        
        if requirements['language'] in self.style_guides:
            requirements['style'] = self.style_guides[requirements['language']]
            
        return requirements

    def _create_implementation_plan(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create structured implementation plan"""
        return [
            {
                "phase": "setup",
                "steps": self._get_setup_steps(requirements)
            },
            {
                "phase": "implementation",
                "steps": self._get_implementation_steps(requirements)
            },
            {
                "phase": "testing",
                "steps": self._get_testing_steps(requirements)
            },
            {
                "phase": "documentation",
                "steps": self._get_documentation_steps(requirements)
            }
        ]

    async def _generate_code(self, 
                           task: str, 
                           plan: List[Dict[str, Any]],
                           tools: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code following the implementation plan"""
        try:
            code_generator = tools.get('code_generator')
            if not code_generator:
                raise ValueError("Code generator tool not available")

            # Generate main implementation
            main_code = await code_generator.execute(
                query=task,
                params={
                    "implementation_plan": plan,
                    "style_guide": self.style_guides.get(
                        self._detect_language(task)
                    )
                }
            )

            # Generate tests if required
            if self.test_requirements['unit_tests']:
                tests = await self._generate_tests(main_code['code'], code_generator)
                main_code['code'] += f"\n\n{tests}"

            return main_code

        except Exception as e:
            raise ValueError(f"Code generation failed: {str(e)}")

    def _calculate_confidence(self, quality_report: Dict[str, Any]) -> float:
        """Calculate confidence based on code quality metrics"""
        base_confidence = 0.7
        
        # Add quality bonuses
        if quality_report['has_docstrings']: base_confidence += 0.1
        if quality_report['has_type_hints']: base_confidence += 0.1
        if quality_report['test_count'] > 0: base_confidence += 0.1
        
        # Subtract complexity penalties
        if quality_report['complexity'] > 10:
            base_confidence -= min((quality_report['complexity'] - 10) * 0.02, 0.2)
            
        return min(base_confidence, 1.0)

    # ... Add other helper methods ...
