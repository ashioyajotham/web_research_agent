import os
import json
import ast
import re
import math
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseTool
import subprocess
import tempfile
import google.generativeai as genai
import numpy as np  # Add this import at the top

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

class CodeAnalysisTool(BaseTool):
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

    def get_description(self) -> str:
        return """Code analysis tool that can:
- Analyze code structure and patterns
- Extract data structures and relationships
- Check for security vulnerabilities
- Calculate code metrics
- Suggest refactoring improvements
Input should be a JSON object with 'command', 'code', and optional 'language' fields."""

class CodeGeneratorTool(BaseTool):
    """Tool for generating code based on requirements"""
    
    ALGORITHM_PATTERNS = {
        'graph': {
            'keywords': ['graph', 'vertex', 'edge', 'path', 'network', 'pagerank', 'dijkstra'],
            'template': """
                import numpy as np
                
                class Graph:
                    def __init__(self):
                        self.nodes = {}
                        self.edges = {}
                    
                    def add_node(self, node):
                        if node not in self.nodes:
                            self.nodes[node] = len(self.nodes)
                            
                    def add_edge(self, from_node, to_node, weight=1):
                        self.add_node(from_node)
                        self.add_node(to_node)
                        if from_node not in self.edges:
                            self.edges[from_node] = {}
                        self.edges[from_node][to_node] = weight
                        
                    def get_adjacency_matrix(self):
                        n = len(self.nodes)
                        matrix = np.zeros((n, n))
                        for from_node, edges in self.edges.items():
                            for to_node, weight in edges.items():
                                matrix[self.nodes[from_node]][self.nodes[to_node]] = weight
                        return matrix
            """
        },
        'pagerank': {
            'keywords': ['pagerank', 'power iteration', 'page rank'],
            'template': """
                import numpy as np
                
                def pagerank(adjacency_matrix: np.ndarray, damping_factor: float = 0.85, iterations: int = 20) -> np.ndarray:
                    \"\"\"
                    Calculate PageRank values using power iteration method.
                    
                    Args:
                        adjacency_matrix: Matrix of web page links
                        damping_factor: Damping factor (typically 0.85)
                        iterations: Number of power iterations
                        
                    Returns:
                        Array of PageRank values for each page
                    \"\"\"
                    n = len(adjacency_matrix)
                    
                    # Normalize adjacency matrix
                    out_degrees = np.sum(adjacency_matrix, axis=1)
                    transition_matrix = adjacency_matrix / out_degrees[:, np.newaxis]
                    
                    # Handle dangling nodes
                    transition_matrix = np.nan_to_num(transition_matrix, 0)
                    
                    # Initialize PageRank values
                    pagerank_vector = np.ones(n) / n
                    
                    # Power iteration
                    for _ in range(iterations):
                        pagerank_vector_next = (1 - damping_factor) / n + damping_factor * transition_matrix.T.dot(pagerank_vector)
                        pagerank_vector = pagerank_vector_next
                        
                    return pagerank_vector
            """
        },
        # ...existing patterns...
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
        """Generate code based on query with algorithm awareness"""
        try:
            prompt = query or kwargs.get('prompt', '')
            template = kwargs.get('template', '')
            
            # Detect algorithm type and get appropriate template
            algo_type, algo_template = self._detect_algorithm_type(prompt)
            
            if template:
                prompt = f"Modify this code:\n{template}\n\nBased on this request:\n{prompt}"
            elif algo_template:
                prompt = self._get_algorithm_prompt(prompt, algo_type, algo_template)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
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
                
            # Verify code quality
            analysis = self._analyze_generated_code(code)
            
            return {
                "success": True,
                "code": code,
                "confidence": analysis['confidence'],
                "metadata": {
                    "algorithm_type": algo_type,
                    "complexity": analysis['complexity'],
                    "quality_score": analysis['quality_score']
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

class CodeAnalysisTool(BaseTool):
    """Tool for analyzing code and providing insights"""
    
    async def execute(self, code: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Analyze code and provide insights"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            system_prompt = """Analyze the provided code and provide insights on:
            - Code quality
            - Potential improvements
            - Best practices adherence
            - Security considerations
            Format as structured JSON with these categories."""
            
            chat = model.start_chat(history=[])
            chat.send_message(system_prompt)
            
            analysis_prompt = f"Code to analyze:\n```\n{code}\n```"
            if context:
                analysis_prompt += f"\nContext: {context}"
                
            response = chat.send_message(analysis_prompt)
            
            return {
                "analysis": response.text,
                "type": "code_analysis",
                "language": self._detect_language(code)
            }
        except Exception as e:
            return {
                "error": str(e),
                "type": "code_analysis_error"
            }

    def get_description(self) -> str:
        return "Analyzes code and provides insights using Gemini"

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        # Simple detection based on common patterns
        if "def " in code or "import " in code:
            return "python"
        if "function" in code or "const" in code:
            return "javascript"
        if "public class" in code:
            return "java"
        if "package main" in code:
            return "go"
        return "unknown"
