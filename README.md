## Project Structure

```
project/
├── agent/
│   ├── __init__.py
│   ├── agent.py          # Core agent class
│   ├── memory.py         # Memory management
│   ├── planner.py        # Task planning and decomposition
│   └── learner.py        # Learning from experiences
├── tools/
│   ├── __init__.py 
│   ├── web_search.py     # Google Search via Serper
│   ├── web_browse.py     # Web page content extraction
│   └── code_tools.py     # Code generation/modification
├── config/
│   └── config.yaml       # API keys and configurations
├── utils/
│   ├── __init__.py
│   └── helpers.py        # Common utilities
├── main.py              # Entry point
├── requirements.txt
└── README.md
```