# Architecture Documentation

## Overview

The Web Research Agent is built on the **ReAct (Reasoning and Acting)** paradigm, implementing a clean, modular architecture that separates concerns and enables easy extensibility.

## Core Principles

1. **Task-Agnostic Design**: No hardcoded logic for specific tasks
2. **Modularity**: Each component has a single, well-defined responsibility
3. **Extensibility**: New tools can be added without modifying core logic
4. **Separation of Concerns**: Clear boundaries between reasoning, execution, and tool implementation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Entry Point                         │
│                           (main.py)                              │
│  • Parses command-line arguments                                 │
│  • Loads configuration from .env                                 │
│  • Initializes components                                        │
│  • Orchestrates task processing                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ReAct Agent Core                          │
│                          (agent.py)                              │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ReAct Loop:                                              │  │
│  │  1. Generate Thought (reasoning about next action)        │  │
│  │  2. Select Action (choose appropriate tool)               │  │
│  │  3. Execute Action (run tool with parameters)             │  │
│  │  4. Process Observation (receive and analyze result)      │  │
│  │  5. Repeat until Final Answer                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  • Maintains conversation history                                │
│  • Builds prompts with context                                   │
│  • Parses LLM responses (Thought/Action/Observation)            │
│  • Manages iteration limits                                      │
└────────────┬────────────────────────────┬───────────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐   ┌───────────────────────────────────┐
│   LLM Interface        │   │      Tool Manager                 │
│     (llm.py)           │   │  (tools/__init__.py)              │
│                        │   │                                   │
│  • Wraps Gemini API    │   │  • Registers tools                │
│  • Handles retries     │   │  • Routes tool calls              │
│  • Manages config      │   │  • Provides descriptions          │
│  • Safety settings     │   │  • Validates parameters           │
└────────────────────────┘   └───────────┬───────────────────────┘
                                         │
                     ┌───────────────────┼───────────────────┐
                     ▼                   ▼                   ▼
           ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
           │   Search Tool   │  │   Scrape Tool   │  │  Code Executor   │
           │  (search.py)    │  │  (scrape.py)    │  │(code_executor.py)│
           │                 │  │                 │  │                  │
           │ • Serper API    │  │ • Fetch URLs    │  │ • Run Python     │
           │ • Google search │  │ • Parse HTML    │  │ • Sandbox exec   │
           │ • Format results│  │ • Extract text  │  │ • Capture output │
           └─────────────────┘  └─────────────────┘  └──────────────────┘
                                         
                                    ┌──────────────────┐
                                    │  File Ops Tool   │
                                    │  (file_ops.py)   │
                                    │                  │
                                    │ • Read files     │
                                    │ • Write files    │
                                    │ • Persistence    │
                                    └──────────────────┘
```

## Component Details

### 1. Main Entry Point (`main.py`)

**Responsibilities:**
- Parse command-line arguments
- Initialize logging system
- Load and validate configuration
- Read tasks from input file
- Initialize the agent with LLM and tools
- Process each task sequentially
- Write results to output file

**Key Functions:**
- `read_tasks()`: Parse task file
- `initialize_agent()`: Set up agent with all components
- `write_results()`: Format and save results
- `main()`: Orchestrate the entire process

### 2. ReAct Agent (`agent.py`)

**Responsibilities:**
- Implement the ReAct reasoning loop
- Build prompts with task context and tool descriptions
- Parse LLM responses for thoughts, actions, and answers
- Execute tools via the Tool Manager
- Maintain execution history
- Handle iteration limits

**Key Classes:**
- `Step`: Data class representing a single reasoning step
- `ReActAgent`: Main agent implementation

**Key Methods:**
- `run(task)`: Execute the ReAct loop for a task
- `_build_prompt()`: Construct prompt with context
- `_parse_response()`: Extract thought/action/answer from LLM
- `_execute_action()`: Run a tool
- `_generate_best_effort_answer()`: Fallback for timeout

**ReAct Loop Detail:**
```
Input: Task description
├─> Iteration 1
│   ├─> Thought: "I need to search for X"
│   ├─> Action: search
│   ├─> Action Input: {"query": "X"}
│   └─> Observation: [Search results]
├─> Iteration 2
│   ├─> Thought: "I should read the first result"
│   ├─> Action: scrape
│   ├─> Action Input: {"url": "..."}
│   └─> Observation: [Page content]
├─> Iteration 3
│   ├─> Thought: "I have enough information"
│   └─> Final Answer: [Complete answer]
Output: Final Answer
```

### 3. LLM Interface (`llm.py`)

**Responsibilities:**
- Wrap Google Gemini API
- Handle API authentication
- Manage generation parameters
- Implement retry logic with exponential backoff
- Handle safety settings
- Process responses

**Key Classes:**
- `LLMInterface`: Manages all LLM interactions

**Key Methods:**
- `generate(prompt)`: Single-turn generation
- `generate_with_history(messages)`: Multi-turn conversation

### 4. Configuration (`config.py`)

**Responsibilities:**
- Load environment variables
- Validate required API keys
- Provide configuration to all components
- Set default values

**Configuration Parameters:**
- API keys (Gemini, Serper)
- Agent settings (iterations, temperature, model)
- Timeout settings (web requests, code execution)

### 5. Tool System

#### Base Tool (`tools/base.py`)

**Abstract Base Class** defining the tool interface:

```python
class Tool(ABC):
    @property
    def name(self) -> str
        # Unique identifier
    
    @property
    def description(self) -> str
        # What the tool does (for LLM)
    
    def execute(self, **kwargs) -> str
        # Tool logic
```

**Design Benefits:**
- Uniform interface for all tools
- Easy to add new tools
- Self-documenting (description used by LLM)
- Type safety with abstract methods

#### Tool Manager (`tools/__init__.py`)

**Responsibilities:**
- Register tools dynamically
- Route tool execution requests
- Provide tool descriptions to agent
- Handle tool errors gracefully

**Key Methods:**
- `register_tool(tool)`: Add a tool to registry
- `get_tool(name)`: Retrieve tool by name
- `execute_tool(name, **kwargs)`: Execute a tool
- `get_tool_descriptions()`: Format all tool descriptions for LLM

#### Search Tool (`tools/search.py`)

**Purpose:** Web search via Serper.dev API

**Parameters:**
- `query`: Search query string

**Returns:**
- Formatted search results with titles, URLs, snippets
- Knowledge graph (if available)
- Answer box (if available)

**Implementation:**
- HTTP POST to Serper API
- JSON response parsing
- Result formatting for readability

#### Scrape Tool (`tools/scrape.py`)

**Purpose:** Fetch and extract content from web pages

**Parameters:**
- `url`: Web page URL

**Returns:**
- Cleaned, readable text content
- Handles HTML, JSON, CSV, plain text
- Special handling for PDFs

**Implementation:**
- HTTP GET with browser-like headers
- BeautifulSoup for HTML parsing
- html2text for markdown conversion
- Content-type detection
- Main content extraction (article, main, etc.)

#### Code Executor Tool (`tools/code_executor.py`)

**Purpose:** Execute Python code for data processing

**Parameters:**
- `code`: Python code string

**Returns:**
- stdout and stderr output
- Return code

**Implementation:**
- Write code to temporary file
- Execute via subprocess
- Capture all output
- Timeout protection
- Cleanup temporary files

**Security Considerations:**
- Runs in same environment (not fully sandboxed)
- Timeout limits prevent infinite loops
- Suitable for research tasks, not production

#### File Operations Tool (`tools/file_ops.py`)

**Purpose:** Read and write files for persistence

**Parameters:**
- `operation`: "read" or "write"
- `path`: File path
- `content`: Content to write (for write operation)

**Returns:**
- File content (for read)
- Success message (for write)

**Implementation:**
- Creates directories as needed
- UTF-8 encoding
- Size limits for safety
- Relative path support

## Data Flow

### Task Processing Flow

```
1. User provides tasks.txt
   │
2. main.py reads and parses tasks
   │
3. For each task:
   │
   ├─> Agent receives task
   │   │
   │   ├─> Loop until answer found or max iterations:
   │   │   │
   │   │   ├─> Agent builds prompt with:
   │   │   │   • Task description
   │   │   │   • Tool descriptions
   │   │   │   • Conversation history
   │   │   │
   │   │   ├─> LLM generates response with:
   │   │   │   • Thought (reasoning)
   │   │   │   • Action (tool name)
   │   │   │   • Action Input (parameters)
   │   │   │   OR
   │   │   │   • Final Answer
   │   │   │
   │   │   ├─> If Action:
   │   │   │   ├─> Tool Manager routes to tool
   │   │   │   ├─> Tool executes
   │   │   │   ├─> Result returned as Observation
   │   │   │   └─> Added to history
   │   │   │
   │   │   └─> If Final Answer:
   │   │       └─> Exit loop
   │   │
   │   └─> Return final answer
   │
   └─> Write result to output file

4. All tasks completed
```

## Design Patterns

### 1. Strategy Pattern (Tools)
Each tool implements the same interface but with different strategies for execution.

### 2. Template Method (ReAct Loop)
The agent defines the skeleton of the algorithm (Thought → Action → Observation) while allowing tools to vary the behavior.

### 3. Registry Pattern (Tool Manager)
Tools register themselves with the manager, enabling dynamic discovery and execution.

### 4. Facade Pattern (LLM Interface)
Provides a simplified interface to the complex Gemini API.

## Error Handling Strategy

### Graceful Degradation
- Network failures: Retry with exponential backoff
- Tool failures: Return error message to agent (LLM decides next step)
- Timeout: Generate best-effort answer from gathered information
- Invalid input: Validation with informative error messages

### Logging
- INFO: Task progress, tool execution
- WARNING: Retries, non-critical issues
- ERROR: Failures with stack traces
- DEBUG: Detailed execution traces

## Extensibility

### Adding a New Tool

1. **Create tool class**:
```python
from tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description for the LLM"
    
    def execute(self, **kwargs) -> str:
        # Implementation
        return result
```

2. **Register in main.py**:
```python
tool_manager.register_tool(MyTool())
```

3. **That's it!** The agent automatically:
   - Discovers the tool
   - Includes it in prompts
   - Routes calls to it

### Customizing Behavior

- **Change LLM**: Modify `llm.py` to support different models
- **Adjust prompts**: Edit `agent.py` prompt templates
- **Add preprocessing**: Extend `main.py` task parsing
- **Custom output**: Modify `write_results()` formatting

## Performance Considerations

### Optimization Strategies

1. **Context Management**: Truncate long observations to stay within token limits
2. **Caching**: LLM responses could be cached (not implemented)
3. **Parallel Execution**: Tasks run sequentially (could parallelize)
4. **Rate Limiting**: Respect API rate limits with backoff

### Scalability

- **Single task**: 30 seconds to 5 minutes depending on complexity
- **API limits**: 
  - Serper free: 2,500 searches/month
  - Gemini free: 60 requests/minute
- **Memory**: Minimal, mostly text processing
- **Storage**: Logs and results only

## Testing Strategy

### Manual Testing
- `check_setup.py`: Verify configuration
- `example_simple.txt`: Quick smoke test
- `tasks.txt`: Full representative task set

### Future Testing
- Unit tests for each tool
- Integration tests for ReAct loop
- Mock LLM for deterministic testing
- Performance benchmarks

## Security Considerations

1. **API Keys**: Stored in .env (never committed)
2. **Code Execution**: Runs in local environment (trusted use)
3. **Web Scraping**: Respects robots.txt (ethical scraping)
4. **Input Validation**: All tool inputs validated
5. **Timeout Protection**: Prevents infinite loops and hangs

## Future Enhancements

### Potential Improvements

1. **Multi-modal Support**: Images, PDFs, videos
2. **Parallel Tool Execution**: Multiple tools at once
3. **Memory System**: Long-term knowledge persistence
4. **Self-Improvement**: Learning from past executions
5. **Tool Chaining**: Automatic pipelines
6. **Better Parsing**: More robust response parsing
7. **Streaming**: Real-time output as agent thinks
8. **Caching**: Avoid redundant searches/scrapes
9. **Evaluation**: Automated quality metrics

### Architecture Evolution

The current architecture supports these enhancements without major refactoring:
- Tools are pluggable
- Agent loop is modular
- LLM interface is abstracted
- Configuration is centralized

## Conclusion

This architecture prioritizes:
- **Simplicity**: Easy to understand and modify
- **Extensibility**: New capabilities without core changes
- **Reliability**: Graceful error handling
- **Maintainability**: Clear separation of concerns
- **Performance**: Efficient within API constraints

The ReAct paradigm provides a powerful framework for building autonomous research agents, and this implementation demonstrates how to build production-quality code following the original paper's methodology.