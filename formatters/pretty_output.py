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
                if 'completion' in output:
                    self._format_completion(task, output)
                elif 'answer' in output:
                    self._format_general_answer(output)
                elif 'chronological_summary' in output:
                    self._format_research_results(output)
                elif 'content' in output:
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

    def _format_completion(self, task: str, output: Dict[str, Any]) -> None:
        """Format completion results with style"""
        completion = output.get('completion', '')
        if completion:
            # Clean up completion (remove redundant task text)
            task_lower = task.lower().rstrip('.')
            completion_lower = completion.lower()
            if completion_lower.startswith(task_lower):
                completion = completion[len(task_lower):].strip()
            
            # Format the complete response
            full_response = f"{task.rstrip('.')} {completion.lstrip()}"
            
            self.console.print(Panel(
                Text(full_response, style="green"),
                title="Completion",
                border_style="cyan",
                padding=(1, 2)
            ))
            
            if output.get('confidence'):
                self.console.print(f"\n[dim]Confidence: {output['confidence']:.2f}[/dim]")

    def _format_general_answer(self, output: Dict[str, Any]) -> None:
        """Format general query answers"""
        answer = output.get('answer', '')
        if answer:
            self.console.print(Panel(
                Markdown(answer),
                title="Answer",
                border_style="blue",
                padding=(1, 2)
            ))
            
            if output.get('confidence'):
                self.console.print(f"\n[dim]Confidence: {output['confidence']:.2f}[/dim]")

    def _format_blog_content(self, content: Any) -> None:
        """Format blog content with improved handling"""
        try:
            content_str = self._extract_content_string(content)
            if not content_str:
                return

            # Extract metadata if available
            metadata = None
            if isinstance(content, dict):
                if 'content' in content and isinstance(content['content'], dict):
                    metadata = content['content'].get('metadata')
                else:
                    metadata = content.get('metadata')

            # Format metadata if available
            if metadata:
                self._format_metadata(metadata)

            # Display content
            self.console.print("\n")  # Add spacing
            self.console.print(Panel(
                Markdown(content_str),
                title=f"Generated Content",
                border_style="green",
                padding=(1, 2),
                expand=True
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
        """Format content metadata with improved layout"""
        meta_table = Table(show_header=False, box=None, padding=(0, 2))
        meta_table.add_column("Key", style="bold blue")
        meta_table.add_column("Value", style="dim")

        for key, value in metadata.items():
            if key not in ["generated_at", "format"]:  # Skip technical metadata
                formatted_key = key.replace("_", " ").title()
                meta_table.add_row(formatted_key, str(value))

        self.console.print("\n[bold]Metadata:[/bold]")
        self.console.print(meta_table)

    def _extract_content_string(self, content: Any) -> str:
        """Extract and clean content string with improved nested dict handling"""
        try:
            # Handle nested content structure
            if isinstance(content, dict):
                # Check for nested content structure
                if 'content' in content and isinstance(content['content'], dict):
                    content_str = content['content'].get('content', '')
                else:
                    content_str = content.get('content', '')
            elif isinstance(content, str):
                content_str = content
            else:
                content_str = str(content) if content is not None else ''

            if not content_str:
                self.console.print("[yellow]No content to display[/yellow]")
                return ''

            # Clean up content
            return self._clean_content(content_str)

        except Exception as e:
            self.console.print(f"[red]Error extracting content: {str(e)}[/red]")
            return str(content)

    def _clean_content(self, content: str) -> str:
        """Clean up content formatting"""
        # Replace escaped characters
        content = content.replace('\\n', '\n')
        content = content.replace('\\t', '\t')
        content = content.replace("\\'", "'")
        content = content.replace('\\"', '"')
        
        # Clean up code blocks
        content = re.sub(r'```python\n', '\n```python\n', content)
        content = re.sub(r'\n```\n', '\n```\n\n', content)
        
        # Clean up headers
        content = re.sub(r'(\n#{1,6})\s+', r'\1 ', content)
        
        # Clean up lists
        content = re.sub(r'(\n-)\s+', r'\1 ', content)
        
        return content.strip()

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

    def _format_research_results(self, output: Dict[str, Any]) -> None:
        """Format research results with timeline and developments"""
        # Display summary if available
        if 'summary' in output:
            self.console.print("\n[bold]Research Summary:[/bold]")
            self.console.print(output['summary'])

        # Display latest developments
        if 'latest_developments' in output and output['latest_developments']:
            self.console.print("\n[bold]Latest Developments:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Date")
            table.add_column("Development")
            table.add_column("Source")
            
            for dev in output['latest_developments']:
                table.add_row(
                    dev.get('date', 'N/A'),
                    dev.get('event', ''),
                    dev.get('source', '')
                )
            self.console.print(table)

        # Display chronological timeline
        if 'chronological_summary' in output and output['chronological_summary'].get('years'):
            self.console.print("\n[bold]Chronological Timeline:[/bold]")
            for year_data in output['chronological_summary']['years']:
                year = year_data['year']
                self.console.print(f"\n[bold blue]{year}[/bold blue]")
                
                for quarter_data in year_data['quarters']:
                    quarter = quarter_data['quarter']
                    self.console.print(f"\n[bold cyan]{quarter}[/bold cyan]")
                    
                    events = quarter_data.get('events', [])
                    if events:
                        for event in events:
                            self.console.print(
                                f"[dim]{event.get('date', '')}:[/dim] {event.get('event', '')}"
                            )

        # Display major milestones
        if 'major_milestones' in output and output['major_milestones']:
            self.console.print("\n[bold]Major Milestones:[/bold]")
            for milestone in output['major_milestones']:
                self.console.print(
                    f"• [dim]{milestone.get('date', '')}:[/dim] {milestone.get('event', '')}"
                )

        # Display sources
        if 'sources' in output and output['sources']:
            self.console.print("\n[bold]Sources:[/bold]")
            for i, source in enumerate(output['sources'], 1):
                self.console.print(f"{i}. {source.get('title', '')}")
                if 'url' in source:
                    self.console.print(f"   [dim]{source['url']}[/dim]")
