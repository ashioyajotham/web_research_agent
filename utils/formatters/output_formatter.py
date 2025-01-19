from typing import Dict, Any, List
from colorama import init, Fore, Back, Style
import json
import textwrap
from enum import Enum

class OutputType(Enum):
    SEARCH = "search"
    LIST = "list"
    CODE = "code"
    ERROR = "error"
    DIRECT = "direct"

class OutputFormatter:
    def __init__(self):
        init()  # Initialize colorama
        self.width = 80
        self.indent = 2
        
    def format_task(self, task: str) -> str:
        return f"\n{Fore.CYAN}Task:{Style.RESET_ALL} {task}"
        
    def format_step(self, step: Dict) -> str:
        tool = step.get('tool', 'unknown')
        params = step.get('params', {})
        return f"\n{Fore.YELLOW}Using {tool}:{Style.RESET_ALL} {params}"
        
    def format_result(self, result: Dict) -> str:
        if not result.get('success', False):
            return self.format_error(result.get('error', 'Unknown error'))
            
        output_type = self.detect_output_type(result)
        if output_type == OutputType.ERROR:
            return self.format_error(result.get('error', 'Unknown error'))
        elif output_type == OutputType.LIST:
            return self.format_list(result)
        elif output_type == OutputType.CODE:
            return self.format_code(result)
        elif output_type == OutputType.SEARCH:
            return self.format_search(result)
        else:
            return self.format_direct(result)
            
    def detect_output_type(self, result: Dict) -> OutputType:
        task = result.get('task', '').lower()
        if 'error' in result:
            return OutputType.ERROR
        elif any(word in task for word in ['list', 'compile', 'enumerate']):
            return OutputType.LIST
        elif any(word in task for word in ['code', 'function', 'program']):
            return OutputType.CODE
        elif result.get('results', [{}])[0].get('tool') == 'web_search':
            return OutputType.SEARCH
        return OutputType.DIRECT
        
    def format_error(self, error: str) -> str:
        return f"\n{Fore.RED}Error: {error}{Style.RESET_ALL}\n"
        
    def format_list(self, result: Dict) -> str:
        items = result.get('results', [{}])[0].get('result', {}).get('results', [])
        output = [f"\n{Fore.GREEN}Results:{Style.RESET_ALL}"]
        for i, item in enumerate(items, 1):
            output.append(f"\n{i}. {Fore.YELLOW}{item.get('title', '')}{Style.RESET_ALL}")
            if 'link' in item:
                output.append(f"   {Fore.BLUE}{item['link']}{Style.RESET_ALL}")
            if 'snippet' in item:
                output.append(f"   {item['snippet']}")
        return '\n'.join(output)
        
    def format_code(self, result: Dict) -> str:
        code = result.get('results', [{}])[0].get('result', {}).get('code', '')
        return f"\n{Fore.CYAN}Generated Code:{Style.RESET_ALL}\n```\n{code}\n```"
        
    def format_search(self, result: Dict) -> str:
        items = result.get('results', [{}])[0].get('result', {}).get('results', [])
        output = [f"\n{Fore.GREEN}Search Results:{Style.RESET_ALL}"]
        for item in items:
            output.append(f"\n{Fore.YELLOW}• {item.get('title', '')}{Style.RESET_ALL}")
            output.append(f"  {Fore.BLUE}{item.get('link', '')}{Style.RESET_ALL}")
            output.append(f"  {item.get('snippet', '')}")
        return '\n'.join(output)
        
    def format_direct(self, result: Dict) -> str:
        answer = result.get('results', [{}])[0].get('result', {}).get('answer', '')
        return f"\n{Fore.GREEN}Answer:{Style.RESET_ALL} {answer}"
        
    def format_results(self, results: Dict) -> str:
        if not results.get("success"):
            return f"{Fore.RED}Error: {results.get('error')}{Style.RESET_ALL}"
            
        output = []
        search_results = results.get("results", [])
        
        for item in search_results:
            output.append(f"\n{Fore.YELLOW}{item.get('title')}{Style.RESET_ALL}")
            output.append(f"{Fore.BLUE}{item.get('link')}{Style.RESET_ALL}")
            output.append(f"{item.get('snippet')}\n")
            
        return "\n".join(output)

    def format_header(self, task: str) -> str:
        border = "=" * self.width
        task_wrapped = textwrap.fill(task, width=self.width-4)
        return f"""
{Fore.CYAN}{border}{Style.RESET_ALL}
  {Fore.YELLOW}{task_wrapped}{Style.RESET_ALL}
{Fore.CYAN}{border}{Style.RESET_ALL}
"""

    def format_search_results(self, results: List[Dict]) -> str:
        if not results:
            return f"{Fore.RED}No results found{Style.RESET_ALL}"
            
        output = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            link = result.get('link', 'No link')
            snippet = result.get('snippet', 'No description')
            
            wrapped_snippet = textwrap.fill(
                snippet, 
                width=self.width-self.indent*2,
                initial_indent=' '*self.indent,
                subsequent_indent=' '*self.indent
            )
            
            output.append(f"""
{Fore.GREEN}[{i}] {Fore.YELLOW}{title}{Style.RESET_ALL}
{Fore.BLUE}{link}{Style.RESET_ALL}
{wrapped_snippet}
""")
        return '\n'.join(output)