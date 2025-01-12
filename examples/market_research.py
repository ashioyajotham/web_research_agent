import os
import sys
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import re
from collections import Counter

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool
from agent.core import Agent, AgentConfig
from formatters.pretty_output import PrettyFormatter

class AnswerExtractor:
    def __init__(self):
        self.patterns = {
            'market_share': [
                r'(\d+\.?\d*)%\s*(?:market share|share)',
                r'market share\D*(\d+\.?\d*)%',
                r'share of\D*(\d+\.?\d*)%'
            ],
            'market_size': [
                r'\$?\s*(\d+\.?\d*)\s*(?:billion|million|trillion)',
                r'market\s*(?:size|value).*?\$?\s*(\d+\.?\d*)\s*(?:billion|million|trillion)',
                r'valued\s*at\s*\$?\s*(\d+\.?\d*)\s*(?:billion|million|trillion)'
            ],
            'rankings': [
                r'(?:1st|first|top|largest|leading).*?([A-Z][A-Za-z0-9\s]+)',
                r'ranked.*?([A-Z][A-Za-z0-9\s]+)'
            ],
            'performance': [
                r'(?:increased|decreased|rose|fell|gained|lost)\s*by\s*(\d+\.?\d*%)',
                r'(\d+\.?\d*%)\s*(?:increase|decrease|gain|loss)'
            ]
        }

    def extract_answer(self, query: str, results: List[Dict[str, str]]) -> str:
        """Extract answer using multiple strategies"""
        # Get all text content
        snippets = [r.get("snippet", "") for r in results]
        titles = [r.get("title", "") for r in results]
        all_text = " ".join(snippets + titles)
        
        # Determine query type and extract accordingly
        query_lower = query.lower()
        
        if "market share" in query_lower:
            return self._extract_market_share(all_text, snippets)
        elif "market size" in query_lower or "valued at" in query_lower:
            return self._extract_market_size(all_text, snippets)
        elif any(x in query_lower for x in ["top", "ranking", "largest", "leading"]):
            return self._extract_rankings(query, snippets)
        elif "performance" in query_lower or "impact" in query_lower:
            return self._extract_performance_metrics(all_text, snippets)
        else:
            return self._extract_general_answer(query, snippets)

    def _extract_market_share(self, text: str, snippets: List[str]) -> str:
        for pattern in self.patterns['market_share']:
            if matches := re.findall(pattern, text):
                # Get the most recent or highest confidence match
                most_relevant = max(matches, key=lambda x: float(x))
                return f"{most_relevant}%"
        return "Could not find specific market share percentage."

    def _extract_market_size(self, text: str, snippets: List[str]) -> str:
        amounts = []
        for pattern in self.patterns['market_size']:
            if matches := re.findall(pattern, text):
                amounts.extend(matches)
        
        if amounts:
            # Try to get most recent or largest value
            return f"${max(amounts, key=lambda x: float(x))} billion"
        return "Could not find specific market size."

    def _extract_rankings(self, query: str, snippets: List[str]) -> str:
        # Look for numbered lists or ranking indicators
        companies = []
        amount_pattern = r'\$?\s*\d+\.?\d*\s*(?:billion|million)'
        
        for snippet in snippets:
            if company_name := re.search(r'([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)', snippet):
                if amount := re.search(amount_pattern, snippet):
                    companies.append((company_name.group(1), amount.group(0)))
                    
        if companies:
            # Sort by amount if available
            companies.sort(key=lambda x: self._parse_amount(x[1]), reverse=True)
            return "\n".join(f"{i+1}. {company} ({amount})" 
                           for i, (company, amount) in enumerate(companies[:5]))
        return "Could not extract ranking information."

    def _extract_performance_metrics(self, text: str, snippets: List[str]) -> str:
        metrics = []
        for pattern in self.patterns['performance']:
            if matches := re.findall(pattern, text):
                metrics.extend(matches)
                
        if metrics:
            most_recent = metrics[0]  # Assume first mention is most recent
            context = next((s for s in snippets if most_recent in s), "")
            return f"Performance change: {most_recent}\nContext: {context}"
        return "Could not find specific performance metrics."

    def _extract_general_answer(self, query: str, snippets: List[str]) -> str:
        # Find most relevant snippet using keyword matching
        query_words = set(query.lower().split())
        scored_snippets = [
            (sum(1 for word in query_words if word in snippet.lower()), snippet)
            for snippet in snippets
        ]
        if scored_snippets:
            return max(scored_snippets, key=lambda x: x[0])[1]
        return "Could not find relevant information."

    def _parse_amount(self, amount_str: str) -> float:
        """Convert amount string to numeric value"""
        try:
            number = float(re.findall(r'\d+\.?\d*', amount_str)[0])
            if 'trillion' in amount_str.lower():
                return number * 1000
            elif 'billion' in amount_str.lower():
                return number
            elif 'million' in amount_str.lower():
                return number / 1000
            return number
        except:
            return 0.0

async def run_market_research():
    # Initialize specialized tools for market research
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
    }
    
    config = AgentConfig(
        max_steps=5,
        min_confidence=0.7,
        timeout=300
    )
    
    agent = Agent(tools=tools, config=config)
    formatter = PrettyFormatter()
    
    # Process market research tasks
    task_file = os.path.join(os.path.dirname(__file__), "tasks/market_research.txt")
    
    with open(task_file, 'r') as f:
        tasks = [line.strip() for line in f.readlines() if line.strip()]
        
    extractor = AnswerExtractor()
    
    for task in tasks:
        result = await agent.process_task(task)
        
        if result.get("success") and "results" in result.get("output", {}):
            answer = extractor.extract_answer(task, result["output"]["results"])
            print(f"\nTask: {task}")
            print(f"Answer: {answer}")
            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(run_market_research())
