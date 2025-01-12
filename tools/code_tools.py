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
    
    def __init__(self):
        super().__init__()
        # Configure model
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.generation_config = {
            "temperature": 0.3,  # Lower temperature for more focused code generation
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

    async def execute(self, prompt: str) -> Dict[str, Any]:
        """Generate code from prompt"""
        try:
            algorithm_type = self._detect_algorithm_type(prompt)
            template = self._get_algorithm_template(algorithm_type)
            
            enhanced_prompt = f"""You are an expert Python programmer. Your task is to generate a complete, production-ready implementation following these requirements:

            {template}

            Task requirements: {prompt}

            The code must include:
            1. Type hints for all functions and methods
            2. Comprehensive error handling
            3. Clear documentation and comments
            4. Example usage in a __main__ block
            5. Unit tests with at least 3 test cases

            Return only the implementation in a code block, no explanations needed.
            The code must be complete and runnable.
            """
            
            model = genai.GenerativeModel('gemini-pro', generation_config=self.generation_config)
            chat = model.start_chat(history=[])
            response = chat.send_message(enhanced_prompt)
            
            code_block = self._extract_code_block(response.text)
            if not code_block:
                # Try again with a more specific prompt
                response = chat.send_message("Please provide only the Python code implementation in a code block")
                code_block = self._extract_code_block(response.text)
                
            if not code_block:
                raise ValueError("Could not generate valid code")
                
            # Validate the generated code
            try:
                ast.parse(code_block)
            except SyntaxError as e:
                raise ValueError(f"Generated code has syntax errors: {str(e)}")
                
            return {
                "code": code_block,
                "language": "python",
                "type": algorithm_type
            }
            
        except Exception as e:
            return {"error": str(e)}

    def _detect_algorithm_type(self, prompt: str) -> str:
        """Detect type of algorithm requested"""
        prompt_lower = prompt.lower()
        
        algorithm_patterns = {
            'mcts': ['mcts', 'monte carlo tree search', 'tree search'],
            'minimax': ['minimax', 'min-max', 'alpha beta'],
            'neural_network': ['neural network', 'deep learning', 'nn'],
            'genetic': ['genetic algorithm', 'evolutionary'],
            'pathfinding': ['pathfinding', 'a*', 'dijkstra']
        }
        
        for algo_type, patterns in algorithm_patterns.items():
            if any(pattern in prompt_lower for pattern in patterns):
                return algo_type
                
        return 'general'

    def _get_algorithm_template(self, algorithm_type: str) -> str:
        """Get template for specific algorithm type"""
        templates = {
            'mcts': """
            Implement a Monte Carlo Tree Search algorithm for Tic-Tac-Toe with:

            Required classes:
            1. TicTacToeState:
                - Board representation as List[List[str]]
                - Methods for moves, legal moves, win check
                - State copying for simulation
                - Pretty printing

            2. MCTSNode:
                - State storage
                - Parent/children connections
                - Visit counts and win statistics
                - UCT calculation with exploration parameter
                - Methods for selection, expansion, simulation

            3. MCTS:
                - search() method to find best move
                - Configurable number of simulations
                - Progress tracking

            4. Game:
                - Human vs AI interface
                - Move validation
                - Board display
                - Main game loop

            Include:
            - Configurable board size (default 3x3)
            - Customizable exploration constant
            - Performance statistics
            - Random seed for reproducibility
            - Clear win/draw detection
            """
        }
        return templates.get(algorithm_type, "Implement the requested functionality with:")

    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract code block from markdown-style text"""
        pattern = r"```(?:\w+)?\n([\s\S]*?)\n```"
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def get_description(self) -> str:
        return "Generates code based on provided requirements using Gemini"

    def _detect_language(self, prompt: str, code_block: str) -> str:
        """Detect programming language from prompt and code block"""
        prompt_lower = prompt.lower()
        code_block_lower = code_block.lower()
        languages = {
            "python": ["python", ".py", "django", "flask"],
            "javascript": ["javascript", "js", "node", "react"],
            "typescript": ["typescript", "ts", "angular"],
            "java": ["java", "spring", "android"],
            "go": ["golang", "go "],
        }
        
        for lang, keywords in languages.items():
            if any(kw in prompt_lower for kw in keywords) or any(kw in code_block_lower for kw in keywords):
                return lang
        return "python"  # default

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
