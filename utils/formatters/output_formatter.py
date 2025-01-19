from typing import Dict, Any, List, Optional
from colorama import init, Fore, Style
from dataclasses import dataclass
import textwrap
import re

@dataclass
class FormatConfig:
    width: int = 100
    indent: int = 2
    max_results: int = 5
    snippet_length: int = 300
    show_metadata: bool = True

class OutputFormatter:
    def __init__(self, config: Optional[FormatConfig] = None):
        init()
        self.config = config or FormatConfig()
        self.styles = {
            'primary': f"{Fore.CYAN}",
            'secondary': f"{Fore.YELLOW}",
            'accent': f"{Fore.GREEN}",
            'link': f"{Fore.BLUE}",
            'warning': f"{Fore.RED}",
            'reset': f"{Style.RESET_ALL}"
        }

    def format_output(self, query: str, results: List[Dict]) -> str:
        """Dynamic output formatting based on content analysis"""
        if not results:
            return self._format_error("No results found")

        content_attributes = self._analyze_content(query, results)
        
        sections = [
            self._format_header(query, content_attributes),
            self._format_main_content(results, content_attributes),
            self._format_metadata(results) if self.config.show_metadata else "",
            self._format_footer(content_attributes)
        ]
        
        return "\n".join(filter(None, sections))

    def format_search_results(self, results: List[Dict]) -> str:
        """Format search results with simple, clear presentation"""
        if not results:
            return f"\n{self.styles['warning']}No relevant information found{self.styles['reset']}\n"
            
        output = []
        for i, result in enumerate(results[:self.config.max_results], 1):
            bullet = "●" if i == 1 else "○"
            output.append(f"""
{self.styles['accent']}{bullet}{self.styles['reset']} {self.styles['secondary']}{result.get('title', '')}{self.styles['reset']}
   {self._wrap_text(result.get('snippet', ''), indent=3)}""")
                
        return "\n".join(output)

    def _analyze_content(self, query: str, results: List[Dict]) -> Dict:
        """Analyze content to determine optimal presentation"""
        return {
            'importance': self._assess_importance(results),
            'complexity': self._assess_complexity(query, results),
            'temporal_relevance': self._has_temporal_data(results),
            'numerical_content': self._has_numerical_data(results),
            'source_diversity': len(set(r.get('link', '').split('/')[2] for r in results)),
            'has_dates': any('date' in r for r in results),
            'key_points': self._extract_key_points(results)
        }

    def _format_main_content(self, results: List[Dict], attributes: Dict) -> str:
        """Format content using our proven search results formatter"""
        return self.format_search_results(results)

    def _wrap_text(self, text: str, indent: int = 0) -> str:
        return textwrap.fill(
            text,
            width=self.config.width - indent,
            initial_indent=' ' * indent,
            subsequent_indent=' ' * indent
        )

    def _center_text(self, text: str) -> str:
        padding = (self.config.width - len(text)) // 2
        return " " * padding + text

    def format_header(self) -> str:
        """Format the overall header for the research results"""
        return f"""
{self.styles['primary']}{'=' * self.config.width}
{self._center_text('Research Results')}
{'=' * self.config.width}{self.styles['reset']}
"""

    def _format_header(self, query: str, attributes: Dict) -> str:
        """Format the header for a specific query"""
        complexity_indicator = "★" * int(attributes['complexity'] * 5) if 'complexity' in attributes else ""
        return f"""
{self.styles['primary']}{'=' * self.config.width}
{self._center_text('Query Analysis')}
{'-' * self.config.width}{self.styles['reset']}
{self._wrap_text(query)}
{self.styles['secondary']}{complexity_indicator}{self.styles['reset']}
{self.styles['primary']}{'-' * self.config.width}{self.styles['reset']}
"""

    def _format_metadata(self, results: List[Dict]) -> str:
        """Format metadata about the search results"""
        if not results:
            return ""
            
        sources = set(r.get('link', '').split('/')[2] for r in results if 'link' in r)
        dates = [r.get('date') for r in results if 'date' in r]
        
        metadata = [
            f"\n{self.styles['secondary']}Sources:{self.styles['reset']} {len(sources)}",
            f"{self.styles['secondary']}Results:{self.styles['reset']} {len(results)}"
        ]
        
        if dates:
            metadata.append(f"{self.styles['secondary']}Date Range:{self.styles['reset']} {min(dates)} - {max(dates)}")
            
        return "\n".join(metadata)

    def _format_footer(self, attributes: Dict = None) -> str:
        """Format the footer with optional attributes summary"""
        return f"\n{self.styles['primary']}{'=' * self.config.width}{self.styles['reset']}\n"

    def format_task_section(self, task_num: int, total_tasks: int, task: str) -> str:
        """Format a task section header"""
        return f"""
{self.styles['secondary']}Task {task_num}/{total_tasks}:{self.styles['reset']}
{self._wrap_text(task)}"""

    def _format_error(self, message: str) -> str:
        """Format error messages"""
        return f"\n{self.styles['warning']}Error: {message}{self.styles['reset']}\n"

    def _has_temporal_data(self, results: List[Dict]) -> bool:
        """Check if results contain temporal data"""
        return any('date' in r for r in results) or any(
            re.search(r'\b\d{4}\b', r.get('snippet', '')) for r in results
        )

    def _has_numerical_data(self, results: List[Dict]) -> bool:
        """Check if results contain significant numerical data"""
        return any(
            len(re.findall(r'[-+]?\d*\.?\d+%?', r.get('snippet', ''))) > 1 
            for r in results
        )

    def _assess_importance(self, results: List[Dict]) -> float:
        """Assess the importance/relevance of results"""
        factors = [
            len([r for r in results if '.gov' in r.get('link', '')]) > 0,
            len([r for r in results if '.edu' in r.get('link', '')]) > 0,
            any(r.get('date') for r in results),
            len(set(r.get('link', '').split('/')[2] for r in results)) > 3
        ]
        return sum(factors) / len(factors)

    def _extract_key_points(self, results: List[Dict]) -> List[str]:
        """Extract key points from results"""
        points = []
        for result in results[:self.config.max_results]:
            sentences = re.split(r'[.!?]+', result.get('snippet', ''))
            points.extend([
                s.strip() for s in sentences 
                if len(s.split()) > 5 and len(s.split()) < 30
                and any(w.islower() for w in s.split())
            ])
        return list(set(points))[:5]  # Return top 5 unique points

    def _format_simple_results(self, results: List[Dict]) -> List[str]:
        """Format basic search results"""
        output = []
        for i, result in enumerate(results[:self.config.max_results], 1):
            output.extend([
                f"\n{self.styles['accent']}Result {i}:{self.styles['reset']}",
                f"{self.styles['secondary']}{result.get('title', '')}{self.styles['reset']}",
                f"{self.styles['link']}{result.get('link', '')}{self.styles['reset']}",
                self._wrap_text(result.get('snippet', ''), indent=2)
            ])
            if result.get('date'):
                output.append(f"{self.styles['secondary']}Date:{self.styles['reset']} {result['date']}")
        return output