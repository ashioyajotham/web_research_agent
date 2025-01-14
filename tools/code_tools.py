import os
import json
import ast
import re
import math
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .base import BaseTool
import subprocess
import tempfile
import google.generativeai as genai
import numpy as np  # Add this import at the top
from collections import defaultdict


@dataclass
class CodeMetrics:
    lines_of_code: int
    cyclomatic_complexity: int
    function_count: int
    class_count: int
    comment_ratio: float

class LanguageDetector:
    PATTERNS = {
        'python': r'\.py$|import \w+|from \w+ import|def \w+\(|class \w+:',
        'javascript': r'\.js$|const |let |function \w+\(|import .* from',
        'typescript': r'\.ts$|interface |type |class \w+ implements',
        'go': r'\.go$|package \w+|func \w+\(|type \w+ struct',
        'java': r'\.java$|public class|private|protected|@Override',
        'rust': r'\.rs$|fn \w+|impl|pub struct|use \w+::'
    }

    @staticmethod
    def detect_language(code: str) -> str:
        for lang, pattern in LanguageDetector.PATTERNS.items():
            if re.search(pattern, code):
                return lang
        return 'unknown'

class DynamicLanguageHandler:
    """Dynamic language detection and handling"""
    def __init__(self):
        self.language_patterns = {}
        self.analysis_strategies = {}
        self._load_language_configs()

    def _load_language_configs(self):
        """Load language configurations dynamically"""
        # Default patterns can be extended at runtime
        self.language_patterns = {
            'python': {'syntax': [r'def \w+', r'class \w+'], 'imports': [r'import \w+', r'from \w+ import']},
            'javascript': {'syntax': [r'function \w+', r'class \w+'], 'imports': [r'require\(', r'import .* from']},
            'typescript': {'syntax': [r'interface \w+', r'type \w+'], 'imports': [r'import \{.*\} from']},
            # More languages can be added dynamically
        }

    def add_language(self, name: str, patterns: Dict[str, List[str]]):
        """Add new language support at runtime"""
        self.language_patterns[name] = patterns

    def detect_language(self, code: str) -> Tuple[str, float]:
        """Detect language with confidence score"""
        scores = {}
        for lang, patterns in self.language_patterns.items():
            score = 0
            for pattern_type, pattern_list in patterns.items():
                matches = sum(bool(re.search(p, code)) for p in pattern_list)
                score += matches / len(pattern_list)
            scores[lang] = score / len(patterns)
        
        best_match = max(scores.items(), key=lambda x: x[1])
        return best_match[0], best_match[1]

class CodeAnalysisTool(BaseTool):
    """Tool for analyzing code and providing insights"""
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata"""
        return {
            "name": "code_analysis",
            "type": "analysis",
            "version": "1.0",
            "capabilities": [
                "code_quality_analysis",
                "security_analysis",
                "performance_analysis",
                "best_practices_check"
            ]
        }

    def get_description(self) -> str:
        """Return tool description"""
        return "Analyzes code and provides insights using Gemini"

    def execute(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            if not isinstance(data, dict):
                return "Error: Input must be a JSON object"
                
            cmd = data.get('command')
            code = data.get('code', '')
            language = data.get('language') or LanguageDetector.detect_language(code)
            
            commands = {
                'analyze': self._analyze_code,
                'extract_data': self._extract_data,
                'generate': self._generate_code,
                'security_check': self._security_check,
                'metrics': self._calculate_metrics,
                'refactor': self._suggest_refactoring
            }
            
            if cmd not in commands:
                return f"Unknown command: {cmd}"
                
            return commands[cmd](code, language)
            
        except Exception as e:
            return f"Error processing code: {str(e)}"

    def _analyze_code(self, code: str, language: str) -> str:
        """Analyzes code structure and patterns"""
        if language == 'python':
            try:
                tree = ast.parse(code)
                analysis = []
                
                # Collect imports
                imports = [node.names[0].name for node in ast.walk(tree) 
                         if isinstance(node, ast.Import)]
                from_imports = [f"{node.module}.{node.names[0].name}" 
                              for node in ast.walk(tree) 
                              if isinstance(node, ast.ImportFrom)]
                
                # Analyze functions
                functions = [node.name for node in ast.walk(tree) 
                           if isinstance(node, ast.FunctionDef)]
                
                # Analyze classes
                classes = [node.name for node in ast.walk(tree) 
                         if isinstance(node, ast.ClassDef)]
                
                return json.dumps({
                    'imports': imports + from_imports,
                    'functions': functions,
                    'classes': classes,
                    'language': language
                }, indent=2)
                
            except SyntaxError as e:
                return f"Python syntax error: {str(e)}"
        
        return f"Code analysis not implemented for {language}"

    def _extract_data(self, code: str, language: str) -> str:
        """Extracts data structures and patterns from code"""
        if language == 'python':
            try:
                tree = ast.parse(code)
                data_structures = {
                    'variables': [],
                    'functions': [],
                    'classes': [],
                    'data_types': []
                }
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                data_structures['variables'].append({
                                    'name': target.id,
                                    'line': target.lineno
                                })
                    elif isinstance(node, ast.FunctionDef):
                        data_structures['functions'].append({
                            'name': node.name,
                            'args': [arg.arg for arg in node.args.args],
                            'line': node.lineno
                        })
                    elif isinstance(node, ast.ClassDef):
                        data_structures['classes'].append({
                            'name': node.name,
                            'bases': [base.id for base in node.bases 
                                    if isinstance(base, ast.Name)],
                            'line': node.lineno
                        })
                
                return json.dumps(data_structures, indent=2)
                
            except SyntaxError as e:
                return f"Python syntax error: {str(e)}"
        
        return f"Data extraction not implemented for {language}"

    def _security_check(self, code: str, language: str) -> str:
        """Checks for common security issues"""
        security_issues = []
        
        # Common security patterns to check
        patterns = {
            'sql_injection': r'execute\s*\(\s*[\'"][^\']*%.*[\'"]',
            'command_injection': r'os\.system\(|subprocess\.call\(|eval\(',
            'hardcoded_secrets': r'password\s*=\s*[\'"][^\'"]+[\'"]|api_key\s*=\s*[\'"][^\'"]+[\'"]',
            'unsafe_deserialization': r'pickle\.loads\(|yaml\.load\(',
            'path_traversal': r'\.\./',
        }
        
        for issue, pattern in patterns.items():
            if re.search(pattern, code, re.IGNORECASE):
                security_issues.append({
                    'type': issue,
                    'description': f'Potential {issue.replace("_", " ")} vulnerability found',
                    'severity': 'HIGH'
                })
        
        return json.dumps(security_issues, indent=2)

    def _calculate_metrics(self, code: str, language: str) -> str:
        """Calculates code quality metrics"""
        if language == 'python':
            try:
                tree = ast.parse(code)
                
                # Calculate basic metrics
                metrics = CodeMetrics(
                    lines_of_code=len(code.splitlines()),
                    cyclomatic_complexity=sum(1 for node in ast.walk(tree) 
                        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler))),
                    function_count=sum(1 for node in ast.walk(tree) 
                        if isinstance(node, ast.FunctionDef)),
                    class_count=sum(1 for node in ast.walk(tree) 
                        if isinstance(node, ast.ClassDef)),
                    comment_ratio=len([l for l in code.splitlines() if l.strip().startswith('#')]) / 
                        len(code.splitlines()) if code.splitlines() else 0
                )
                
                return json.dumps(metrics.__dict__, indent=2)
                
            except SyntaxError as e:
                return f"Python syntax error: {str(e)}"
        
        return f"Metrics calculation not implemented for {language}"

    def _suggest_refactoring(self, code: str, language: str) -> str:
        """Suggests code refactoring improvements"""
        suggestions = []
        
        if language == 'python':
            try:
                tree = ast.parse(code)
                
                # Check function length
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_code = ast.get_source_segment(code, node)
                        if func_code and len(func_code.splitlines()) > 20:
                            suggestions.append({
                                'type': 'long_function',
                                'location': f'Function {node.name}',
                                'suggestion': 'Consider breaking down into smaller functions'
                            })
                
                # Check class complexity
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        method_count = sum(1 for n in ast.walk(node) 
                            if isinstance(n, ast.FunctionDef))
                        if method_count > 10:
                            suggestions.append({
                                'type': 'complex_class',
                                'location': f'Class {node.name}',
                                'suggestion': 'Consider splitting into smaller classes'
                            })
                
                return json.dumps(suggestions, indent=2)
                
            except SyntaxError as e:
                return f"Python syntax error: {str(e)}"
        
        return f"Refactoring suggestions not implemented for {language}"

class CodeGeneratorTool(BaseTool):
    """Tool for generating code based on requirements"""
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata"""
        return {
            "name": "code_generator",
            "type": "generation",
            "version": "1.0",
            "capabilities": [
                "code_generation",
                "algorithm_implementation",
                "template_adaptation",
                "pattern_based_generation"
            ]
        }

    def __init__(self):
        super().__init__()
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro',
            generation_config={
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )

    async def execute(self, query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate code based on query with improved algorithm handling"""
        try:
            prompt = query or kwargs.get('prompt', '')
            template = kwargs.get('template', '')
            algo_type = kwargs.get('algorithm_type', '')
            
            # Enhanced prompt for code generation
            generation_prompt = f"""Generate a complete Python implementation for: {prompt}

            Requirements:
            1. Include proper class and method documentation
            2. Add type hints
            3. Include error handling
            4. Add example usage
            5. Follow Python best practices
            
            Return the implementation in a code block.
            """
            
            # Generate response
            response = self.model.generate_content(generation_prompt)
            
            if not response.text:
                return {
                    "success": False, 
                    "error": "No code generated",
                    "code": None
                }
                
            code = self._extract_code_block(response.text)
            if not code:
                return {
                    "success": False,
                    "error": "Could not extract valid code from response",
                    "code": None
                }
                
            # Add explanation and examples
            explanation_prompt = f"Explain how the following code works:\n```python\n{code}\n```"
            explanation_response = self.model.generate_content(explanation_prompt)
            
            return {
                "success": True,
                "code": code,
                "explanation": explanation_response.text if explanation_response.text else "",
                "confidence": 0.8,
                "metadata": {
                    "algorithm_type": algo_type,
                    "language": "python"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "code": None
            }

    def _detect_algorithm_type(self, prompt: str) -> tuple[str, str]:
        """Detect algorithm type from prompt with improved PageRank detection"""
        prompt_lower = prompt.lower()
        
        # Check for PageRank specifically first
        if any(kw in prompt_lower for kw in self.ALGORITHM_PATTERNS['pagerank']['keywords']):
            return 'pagerank', self.ALGORITHM_PATTERNS['pagerank']['template']
            
        # Then check other algorithms
        for algo_type, pattern in self.ALGORITHM_PATTERNS.items():
            if algo_type != 'pagerank' and any(keyword in prompt_lower for keyword in pattern['keywords']):
                return algo_type, pattern['template']
                
        return 'generic', ''

    def _get_algorithm_prompt(self, base_prompt: str, algo_type: str, template: str) -> str:
        """Get enhanced prompt for specific algorithm type"""
        if algo_type == 'pagerank':
            return f"""
            Implement a solution for this PageRank problem:
            {base_prompt}
            
            Use this template and numpy for efficient matrix operations:
            ```python
            {template}
            ```
            
            Requirements:
            1. Create the adjacency matrix for the given graph
            2. Implement PageRank with the specified damping factor
            3. Run for the specified number of iterations
            4. Return the PageRank values for each page
            5. Include example usage with the given graph
            
            Return complete implementation and example usage.
            """
        
        # ...existing prompt generation for other algorithm types...

    def _analyze_generated_code(self, code: str) -> Dict[str, Any]:
        """Analyze generated code quality"""
        try:
            tree = ast.parse(code)
            
            # Calculate metrics
            complexity = sum(1 for node in ast.walk(tree) 
                if isinstance(node, (ast.If, ast.For, ast.While, ast.FunctionDef)))
            
            has_docstrings = any(isinstance(node, ast.Expr) and 
                isinstance(node.value, ast.Str) for node in ast.walk(tree))
            
            has_type_hints = any(isinstance(node, ast.AnnAssign) for node in ast.walk(tree))
            
            # Calculate quality score
            quality_score = 0.7  # Base score
            if has_docstrings: quality_score += 0.1
            if has_type_hints: quality_score += 0.1
            if complexity < 10: quality_score += 0.1
            
            return {
                'complexity': complexity,
                'quality_score': quality_score,
                'confidence': quality_score
            }
            
        except Exception:
            return {
                'complexity': -1,
                'quality_score': 0.5,
                'confidence': 0.5
            }

    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract code block from Gemini response"""
        import re
        pattern = r"```(?:python)?\n([\s\S]*?)\n```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return text.strip()  # Return full text if no code block found

    def get_description(self) -> str:
        return "Generates code based on requirements, with special handling for algorithms like MCTS"

class AdaptiveCodeGenerator(CodeGeneratorTool):
    """More flexible code generation tool"""
    def __init__(self):
        super().__init__()
        self.language_handler = DynamicLanguageHandler()
        self.pattern_cache = {}
        self.generation_history = []
        
    async def execute(self, query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            # Get context from core agent if available
            context = kwargs.get('context', {})
            
            # Detect required language and paradigm
            language, confidence = self.language_handler.detect_language(query)
            
            # Generate with context awareness
            generation_config = self._build_generation_config(
                query, language, context
            )
            
            # Use core's pattern learning if available
            if pattern_learner := context.get('pattern_learner'):
                similar_patterns = pattern_learner.find_similar_patterns(query)
                if similar_patterns:
                    generation_config['template'] = self._adapt_template(
                        similar_patterns[0], language
                    )
            
            response = await self._generate_with_config(generation_config)
            
            # Learn from generation
            self._update_pattern_cache(query, response)
            
            return {
                "success": True,
                "code": response.get('code'),
                "language": language,
                "confidence": confidence * response.get('quality_score', 0.8),
                "metadata": {
                    "generation_config": generation_config,
                    "context_used": bool(context)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_generation_config(self, query: str, language: str, context: Dict) -> Dict[str, Any]:
        """Build dynamic generation configuration"""
        config = {
            "language": language,
            "style": self._detect_code_style(query),
            "complexity": self._estimate_complexity(query),
            "patterns": self._get_relevant_patterns(query),
            "context": context
        }
        
        if context.get('temporal_context'):
            config['temporal_context'] = context['temporal_context']
            
        return config

    def _detect_code_style(self, query: str) -> Dict[str, float]:
        """Detect required code style preferences"""
        styles = {
            'functional': sum(term in query.lower() for term in ['map', 'reduce', 'filter', 'pure']),
            'object_oriented': sum(term in query.lower() for term in ['class', 'object', 'inherit']),
            'procedural': sum(term in query.lower() for term in ['procedure', 'function', 'step'])
        }
        total = sum(styles.values()) or 1
        return {k: v/total for k, v in styles.items()}

class AdaptiveCodeAnalyzer(CodeAnalysisTool):
    """More flexible code analysis tool"""
    def __init__(self):
        super().__init__()
        self.language_handler = DynamicLanguageHandler()
        self.analysis_patterns = defaultdict(list)
        
    async def execute(self, code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        try:
            # Detect language with confidence
            language, confidence = self.language_handler.detect_language(code)
            
            # Build analysis strategy
            strategy = self._build_analysis_strategy(language, context)
            
            # Perform analysis with context awareness
            analysis_results = await self._analyze_with_strategy(code, strategy)
            
            # Learn from analysis
            if context and context.get('learning_enabled'):
                self._learn_from_analysis(code, analysis_results)
            
            return {
                "success": True,
                "analysis": analysis_results,
                "language": language,
                "confidence": confidence,
                "metadata": {
                    "strategy_used": strategy['type'],
                    "context_applied": bool(context)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_analysis_strategy(self, language: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Build dynamic analysis strategy"""
        strategy = {
            "type": "adaptive",
            "language": language,
            "patterns": self.analysis_patterns[language],
            "metrics": self._get_language_metrics(language)
        }
        
        if context:
            strategy.update(self._adapt_to_context(context))
            
        return strategy

class AlgorithmPattern:
    """Flexible algorithm pattern representation"""
    def __init__(self, name: str, category: str, complexity: str = "medium"):
        self.name = name
        self.category = category
        self.complexity = complexity
        self.patterns = []
        self.implementations = {}
        self.usage_count = 0
        self.success_rate = 0.0
        self.adaptations = []

    def add_pattern(self, pattern: Dict[str, Any]):
        """Add a new implementation pattern"""
        self.patterns.append({
            'keywords': pattern.get('keywords', []),
            'structure': pattern.get('structure', {}),
            'constraints': pattern.get('constraints', []),
            'template': pattern.get('template', ''),
            'adaptations': pattern.get('adaptations', [])
        })

    def adapt_to_context(self, context: Dict[str, Any]) -> str:
        """Adapt template based on context"""
        template = self.get_best_template(context)
        return self._customize_template(template, context)

class AdaptiveAlgorithmRegistry:
    """Dynamic algorithm pattern registry"""
    def __init__(self):
        self.algorithms = {}
        self.categories = {
            'graph': ['path_finding', 'network_analysis', 'tree_operations'],
            'optimization': ['search', 'sort', 'scheduling'],
            'ml': ['classification', 'regression', 'clustering'],
            'data_structures': ['lists', 'trees', 'hash_tables'],
            'math': ['numerical', 'statistical', 'algebraic']
        }
        self._initialize_base_patterns()

    def _initialize_base_patterns(self):
        """Initialize with basic adaptable patterns"""
        self.register_algorithm({
            'name': 'graph_ops',
            'category': 'graph',
            'patterns': [{
                'keywords': ['graph', 'node', 'edge', 'path', 'network'],
                'structure': {
                    'required_components': ['node_storage', 'edge_handling', 'traversal'],
                    'optional_components': ['weights', 'directions', 'labels']
                },
                'template': self._get_flexible_graph_template()
            }]
        })
        # Add more base patterns...

    def register_algorithm(self, config: Dict[str, Any]):
        """Register new algorithm pattern"""
        algo = AlgorithmPattern(
            name=config['name'],
            category=config['category']
        )
        for pattern in config['patterns']:
            algo.add_pattern(pattern)
        self.algorithms[config['name']] = algo

    def _get_flexible_graph_template(self) -> str:
        """Generate flexible graph template"""
        return '''
        class Graph:
            def __init__(self, directed: bool = False, weighted: bool = False):
                self.nodes = {}
                self.edges = {}
                self.directed = directed
                self.weighted = weighted
                self.metadata = {}
            
            def add_node(self, node, **attributes):
                """Add node with flexible attributes"""
                if node not in self.nodes:
                    self.nodes[node] = {
                        'id': len(self.nodes),
                        'attributes': attributes,
                        'edges': set()
                    }
            
            def add_edge(self, start, end, **properties):
                """Add edge with flexible properties"""
                self.add_node(start)
                self.add_node(end)
                
                edge_data = {
                    'properties': properties,
                    'start': start,
                    'end': end
                }
                
                if start not in self.edges:
                    self.edges[start] = {}
                self.edges[start][end] = edge_data
                self.nodes[start]['edges'].add(end)
                
                if not self.directed:
                    if end not in self.edges:
                        self.edges[end] = {}
                    self.edges[end][start] = edge_data
                    self.nodes[end]['edges'].add(start)
            
            def get_neighbors(self, node):
                """Get node neighbors with flexible filtering"""
                return self.nodes[node]['edges']
            
            def apply_algorithm(self, algorithm_name: str, **params):
                """Apply any graph algorithm with flexible parameters"""
                if hasattr(self, algorithm_name):
                    return getattr(self, algorithm_name)(**params)
                raise ValueError(f"Algorithm {algorithm_name} not implemented")
        '''

    def find_matching_algorithm(self, query: str, context: Dict[str, Any]) -> Optional[AlgorithmPattern]:
        """Find best matching algorithm based on query and context"""
        scores = {}
        query_lower = query.lower()
        
        for name, algo in self.algorithms.items():
            score = 0
            # Match keywords
            for pattern in algo.patterns:
                keyword_matches = sum(k in query_lower for k in pattern['keywords'])
                score += keyword_matches * 0.5
                
                # Match structure requirements
                if 'structure' in pattern:
                    struct_matches = self._match_structure(pattern['structure'], context)
                    score += struct_matches * 0.3
                
                # Consider past success rate
                score *= (1 + algo.success_rate * 0.2)
            
            scores[name] = score
        
        best_match = max(scores.items(), key=lambda x: x[1])
        return self.algorithms[best_match[0]] if best_match[1] > 0.5 else None

    def _match_structure(self, structure: Dict, context: Dict) -> float:
        """Match structural requirements with context"""
        if 'required_components' not in structure:
            return 0.0
            
        required = set(structure['required_components'])
        available = set(context.get('components', []))
        
        match_ratio = len(required.intersection(available)) / len(required)
        return match_ratio

class AdaptiveCodeGenerator(CodeGeneratorTool):
    """More flexible code generation with adaptive algorithms"""
    def __init__(self):
        super().__init__()
        self.algorithm_registry = AdaptiveAlgorithmRegistry()
        self.language_handler = DynamicLanguageHandler()
        
    async def execute(self, query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            context = kwargs.get('context', {})
            language, confidence = self.language_handler.detect_language(query)
            
            # Try to find matching algorithm pattern
            if algorithm := self.algorithm_registry.find_matching_algorithm(query, context):
                template = algorithm.adapt_to_context(context)
                code = await self._generate_with_template(query, template, context)
            else:
                code = await self._generate_from_scratch(query, context)
            
            return {
                "success": True,
                "code": code,
                "language": language,
                "confidence": confidence,
                "metadata": {
                    "algorithm_used": algorithm.name if algorithm else None,
                    "context_applied": bool(context)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# ...rest of the existing code...
