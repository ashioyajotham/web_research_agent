# Web Research Agent

An AI-powered agent that can perform web research, code analysis, and code generation tasks using Google's Gemini and various tools.

## Setup

1. Create a .env file with your API keys:
```
SERPER_API_KEY=your_serper_api_key
GEMINI_API_KEY=your_gemini_api_key
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the agent with a task file:
```bash
python agent.py tasks.txt results.json
```

Each line in tasks.txt should contain one task. Tasks can include:
- Research queries
- Code generation requests
- Technical analysis tasks
- Architecture design tasks

Results will be written to results.json.

## Example Tasks

Research tasks:
```
Find the most cited academic papers in machine learning from 2023.
What were the major archaeological discoveries announced in 2023?
```

Coding tasks:
```
Create a Python function that implements the PageRank algorithm.
Write a React component that implements infinite scrolling.
```

## Adding New Tools

1. Create a new tool class in tools/ that inherits from BaseTool
2. Implement the execute() and get_description() methods
3. Add the tool to the tools registry in agent.py

## Project Structure

```plaintext
web_research_agent/
├── agent/
│   ├── __init__.py
│   ├── core.py           # Core agent functionality
│   ├── planner.py        # Strategic planning
│   ├── memory.py         # Experience management
│   ├── executor.py       # Task execution
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── base.py       # Base strategy interface
│   │   ├── research.py   # Research strategies
│   │   └── coding.py     # Coding strategies
│   ├── reflection/
│   │   ├── __init__.py
│   │   ├── evaluator.py  # Self-evaluation
│   │   └── learner.py    # Learning from experience
│   └── utils/
│       ├── __init__.py
│       └── prompts.py     # Prompt templates
├── tools/
│   ├── __init__.py
│   ├── base.py
│   ├── google_search.py
│   ├── web_scraper.py
│   └── code_tools.py
├── examples/
│   ├── tasks/
│   │   ├── market_research.txt
│   │   ├── tech_analysis.txt
│   │   └── environmental_data.txt
│   ├── market_research.py
│   ├── tech_analyzer.py
│   └── sustainability_tracker.py
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_planner.py
│   └── test_tools.py
├── .env
├── requirements.txt
├── README.md
├── agent.py
└── tasks.txt
```