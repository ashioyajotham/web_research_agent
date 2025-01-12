import os
import json
import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseTool
import subprocess
import tempfile

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
