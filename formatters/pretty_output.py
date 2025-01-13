from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.syntax import Syntax
import re

class PrettyFormatter:
    def __init__(self):
        self.console = Console()

    def format_task_result(self, task: str, result: Dict[str, Any]) -> None:
        """Format a task result with error handling"""
        try:
            self.console.print(f"[bold blue]Task:[/bold blue] {task}")
            
            if not result.get('success'):
                self.console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
                return

            output = result.get('output', {})
            if not output:
                self.console.print("[yellow]No output available[/yellow]")
                return

            # Handle different output types
            if isinstance(output, dict):
                if 'content' in output:
                    self._format_blog_content(output['content'])
                elif 'direct_answer' in output:
                    self._format_direct_answer(output)
                elif 'results' in output:
                    self._format_search_results(output.get('results', []))
                elif 'code' in output:
                    self._format_code_output(output)
            else:
                self.console.print(str(output))

        except Exception as e:
            self.console.print(f"[red]Formatting error: {str(e)}[/red]")

    def _format_blog_content(self, content: Any) -> None:
        """Format blog content with improved handling"""
        try:
            content_str = self._extract_content_string(content)
            if not content_str:
                return

            # Clean up markdown formatting
            content_str = self._clean_markdown(content_str)
            
            # Add syntax highlighting
            content_str = self._highlight_code_blocks(content_str)

            # Format metadata if available
            if isinstance(content, dict) and 'metadata' in content:
                self._format_metadata(content['metadata'])

            # Display content in panel
            self.console.print(Panel(
                Markdown(content_str),
                title=f"Generated Content ({content.get('type', 'article')})",
                border_style="green",
                padding=(1, 2)
            ))

        except Exception as e:
            self.console.print(f"[red]Content formatting error: {str(e)}[/red]")
            self.console.print(str(content))

    def _highlight_code_blocks(self, content: str) -> str:
        """Add syntax highlighting to code blocks"""
        import re
        def replace_code_block(match):
            lang = match.group(1) or 'python'
            code = match.group(2)
            return f"```{lang}\n{code}\n```"

        pattern = r"```(\w+)?\n(.*?)\n```"
        return re.sub(pattern, replace_code_block, content, flags=re.DOTALL)

    def _format_metadata(self, metadata: Dict[str, Any]) -> None:
        """Format content metadata"""
        meta_table = Table(show_header=False, box=None)
        meta_table.add_column("Key", style="bold blue")
        meta_table.add_column("Value", style="dim")

        for key, value in metadata.items():
            if key != "generated_at":  # Handle timestamp separately
                meta_table.add_row(key.replace("_", " ").title(), str(value))

        self.console.print(meta_table)

    def _extract_content_string(self, content: Any) -> str:
        """Extract and clean content string"""
        try:
            if isinstance(content, dict):
                content_str = content.get('content', '')
                if not content_str:
                    content_str = (content.get('text', '') or 
                                 content.get('body', '') or 
                                 content.get('article', ''))
            elif isinstance(content, str):
                content_str = content
            else:
                content_str = str(content) if content is not None else ''

            if not content_str:
                self.console.print("[yellow]No content to display[/yellow]")
                return ''

            # Clean up escaped newlines and spaces
            content_str = content_str.replace('\\n', '\n')
            content_str = content_str.replace('\\t', '\t')
            content_str = content_str.strip()

            return content_str

        except Exception as e:
            self.console.print(f"[red]Error extracting content: {str(e)}[/red]")
            return str(content)

    def _clean_markdown(self, text: str) -> str:
        """Clean up markdown formatting"""
        # Fix headers that might be escaped
        text = re.sub(r'\\#', '#', text)
        
        # Fix list items
        text = re.sub(r'\\-', '-', text)
        
        # Fix code blocks
        text = re.sub(r'\\`\\`\\`', '```', text)
        
        # Fix inline code
        text = re.sub(r'\\`', '`', text)
        
        return text.strip()

    def _format_direct_answer(self, output: Dict[str, Any]) -> None:
        """Format direct answer results with better cleaning"""
        answer = output.get('direct_answer')
        if not answer:
            return

        # Clean up the answer
        cleaned_answer = self._clean_answer_text(answer)
        
        # Format based on answer type
        if "richest" in output.get('query', '').lower():
            self._format_richest_person(cleaned_answer)
        else:
            self.console.print(Panel(
                str(cleaned_answer),
                title="Direct Answer",
                border_style="blue"
            ))

    def _clean_answer_text(self, text: str) -> str:
        """Clean up answer text"""
        if not text:
            return text

        # Remove common prefixes
        prefixes_to_remove = [
            "Richest People",
            "The Richest",
            "The Person",
            "Person",
            "According to",
            "From",
            "Source:",
            "Wikipedia:",
            "Reuters:"
        ]
        
        cleaned = text
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned.strip()

    def _format_richest_person(self, answer: str) -> None:
        """Special formatting for richest person queries"""
        parts = answer.split('(', 1)
        name = parts[0].strip()
        details = f"({parts[1]}" if len(parts) > 1 else ""

        self.console.print(Panel(
            f"[bold blue]{name}[/bold blue]\n[dim]{details}[/dim]",
            title="Richest Person",
            border_style="blue"
        ))

    def _format_search_results(self, results: list) -> None:
        """Format search results in a table"""
        if not results:
            self.console.print("[yellow]No search results found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Title")
        table.add_column("Snippet")
        
        for result in results[:5]:  # Limit to top 5 results
            title = result.get('title', 'No title')
            snippet = result.get('snippet', 'No snippet')
            table.add_row(title, snippet)

        self.console.print(table)

    def _format_code_output(self, output: Dict[str, Any]) -> None:
        """Format code generation output"""
        code = output.get('code')
        if code:
            self.console.print(Panel(
                f"```python\n{code}\n```",
                title="Generated Code",
                border_style="cyan"
            ))

    def _show_sources(self, sources: List[Dict[str, Any]]) -> None:
        """Display reference sources"""
        self.console.print("\n[bold]Sources:[/bold]")
        for i, source in enumerate(sources, 1):
            if isinstance(source, dict):
                title = source.get("title", source.get("source", "Unknown"))
                url = source.get("link", source.get("url", ""))
                self.console.print(f"{i}. {title}")
                if url:
                    self.console.print(f"   [dim]{url}[/dim]")
            elif isinstance(source, (list, tuple)) and len(source) == 2:
                title, url = source
                self.console.print(f"{i}. {title}")
                self.console.print(f"   [dim]{url}[/dim]")

    def _format_knowledge_graph(self, kg_data: Dict[str, Any]) -> None:
        """Format knowledge graph data"""
        if not kg_data:
            return

        # Create a stylized panel for knowledge graph
        kg_content = [
            f"[bold]{kg_data.get('title', '')}[/bold]",
            f"[dim]{kg_data.get('type', '')}[/dim]\n",
            kg_data.get('description', ''),
            "\n[bold]Attributes:[/bold]"
        ]

        # Add attributes
        for key, value in kg_data.get('attributes', {}).items():
            kg_content.append(f"• {key.replace('_', ' ').title()}: {value}")

        # Add links if available
        if kg_data.get('links'):
            kg_content.append("\n[bold]Related Links:[/bold]")
            for link in kg_data['links']:
                kg_content.append(f"• {link['title']}")

        self.console.print(Panel(
            "\n".join(kg_content),
            title="Knowledge Graph",
            border_style="cyan"
        ))
