# Web Research Agent

An experimental research implementation of the ReAct (Reasoning + Acting) paradigm applied to web research tasks. This project explores systematic approaches to information-seeking problems through structured analysis of tasks, adaptive search strategies, and context-aware synthesis methods.

> **Research Focus**: This project implements and extends the ReAct framework as a platform for investigating task-adaptive reasoning patterns. It is intended as an academic exploration rather than a production system, focusing on understanding how structured approaches to web research can be systematized and evaluated.

## Research Contributions

- **Dynamic Task Analysis**: Pattern recognition system that determines expected answer types and synthesis strategies from question structure alone
- **Multi-Strategy Synthesis**: Four distinct synthesis approaches (extract-and-verify, aggregate-and-filter, collect-and-organize, comprehensive-synthesis) selected based on task characteristics
- **Adaptive Answer Formatting**: System produces direct answers to questions rather than defaulting to entity tables or fixed formats
- **Robust Parameter Resolution**: Multiple fallback strategies for handling incomplete or ambiguous web search results

## Features

### Research Implementation Features
- **Task-Adaptive Reasoning**: Analyzes task structure to determine appropriate synthesis strategies
- **Dynamic Answer Synthesis**: Four synthesis modes that adapt to question types (factual lookup, comparison, aggregation, comprehensive analysis)
- **Entity-Aware Processing**: Extracts and tracks entities while maintaining focus on answering the specific question asked
- **Flexible Search Planning**: Creates search strategies based on information targets identified in the task
- **Robust Error Handling**: Multiple fallback strategies for URL resolution and content extraction

### Practical Tool Features  
- **Multi-Criteria Task Handling**: Processes complex queries with multiple conditions
- **Structured Output**: Formats findings appropriately for the question type
- **Code Generation**: Generates analysis code when computational tasks are detected
- **Source Verification**: Validates information across multiple sources
- **Progress Tracking**: Detailed logging of reasoning and synthesis processes

## Architecture & ReAct Implementation

This project implements the ReAct paradigm with dynamic task analysis and adaptive synthesis:

```mermaid
graph TD
    A[Main] --> B[WebResearchAgent]
    B --> C1[Memory]
    B --> C2[Planner]
    B --> C3[Comprehension]
    B --> C4[ToolRegistry]
    
    %% Enhanced ReAct: Dynamic Reasoning
    C3 -->|"Dynamic Analysis"| G1[Task Analysis]
    G1 --> G2[Answer Type Detection]
    G1 --> G3[Information Target ID]
    G1 --> G4[Output Structure Inference]
    
    C2 -->|"Adaptive Planning"| D[Plan]
    D -->|Contains| E[PlanSteps]
    
    %% ReAct: Acting component
    C4 -->|Registers| F1[SearchTool]
    C4 -->|Registers| F2[BrowserTool]
    C4 -->|Registers| F3[CodeGeneratorTool]
    C4 -->|Registers| F4[PresentationTool]
    
    %% Enhanced ReAct: Multi-Strategy Synthesis
    C3 -->|"Strategy Selection"| S1[Extract & Verify]
    C3 -->|"Strategy Selection"| S2[Aggregate & Filter]
    C3 -->|"Strategy Selection"| S3[Collect & Organize]
    C3 -->|"Strategy Selection"| S4[Comprehensive Synthesis]
    
    %% ReAct: Observation component
    C1 -->|"Stores"| M1[Results & Entities]
    
    %% ReAct: Iteration cycle
    B -->|"1. Analyze Task"| G1
    G1 -->|"2. Plan Strategy"| C2
    C2 -->|"3. Execute Actions"| C4
    C4 -->|"4. Synthesize Answer"| S1
    S1 -->|"5. Verify & Refine"| B
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style G1 fill:#fbb,stroke:#333,stroke-width:2px
    style S1 fill:#bfb,stroke:#333,stroke-width:2px
    style C1 fill:#bbf,stroke:#333
    style C2 fill:#bbf,stroke:#333
    style C3 fill:#bbf,stroke:#333
    style C4 fill:#bbf,stroke:#333
    style F1 fill:#bfb,stroke:#333
    style F2 fill:#bfb,stroke:#333
    style F3 fill:#bfb,stroke:#333
    style F4 fill:#bfb,stroke:#333
```

### Workflow Explanation

The diagram above illustrates how the Web Research Agent processes research tasks:

1. **Task Analysis Phase**: 
   - When a user submits a research question, the system first analyzes the task structure
   - The Comprehension component uses pattern recognition to detect answer types (factual, comparative, list-based, etc.)
   - It identifies specific information targets needed to answer the question
   - It determines the appropriate output structure for the anticipated answer

2. **Planning Phase**:
   - Based on the task analysis, the Planner creates a series of search strategies
   - It generates concrete plan steps targeting the identified information needs
   - Each plan step specifies what information to retrieve and how to process it

3. **Action Phase**:
   - The ToolRegistry orchestrates the execution of research tools:
     - SearchTool finds relevant information sources
     - BrowserTool extracts content from web pages
     - CodeGeneratorTool creates analysis scripts when needed
     - PresentationTool formats findings appropriately

4. **Synthesis Phase**:
   - Based on the question type, one of four synthesis strategies is selected:
     - Extract-and-Verify for factual questions
     - Aggregate-and-Filter for comparative analyses
     - Collect-and-Organize for list-building tasks
     - Comprehensive-Synthesis for complex, multi-faceted questions
   - The Memory component provides context by storing intermediate findings and entities

5. **Refinement Loop**:
   - If the synthesized answer is incomplete, the system may return to planning
   - This iterative process continues until a satisfactory answer is produced
   - The final output is tailored to directly address the specific question asked

This research implementation demonstrates how a structured approach to web research can adapt to different question types without relying on hardcoded rules.

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ashioyajotham/web_research_agent.git
   cd web_research_agent
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Research Environment Setup

The system requires the following external services for operation:

1. **Gemini API**: Language model for reasoning and synthesis
2. **Serper API**: Web search results for information gathering

### Setting up API keys

#### Option 1: .env file (Recommended for research)

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key
SERPER_API_KEY=your_serper_api_key
```

#### Option 2: Environment Variables

```bash
export GEMINI_API_KEY=your_gemini_api_key
export SERPER_API_KEY=your_serper_api_key
```

#### Option 3: Programmatic Configuration

```python
from config.config_manager import init_config

config = init_config()
config.update('gemini_api_key', 'your_gemini_api_key')
config.update('serper_api_key', 'your_serper_api_key')
```

### Research Configuration Parameters

These parameters control the system's behavior and can be modified for experimental purposes:

| Parameter | Environment Variable | Description | Default |
|-----------|---------------------|-------------|---------|
| gemini_api_key | GEMINI_API_KEY | API key for Gemini LLM | - |
| serper_api_key | SERPER_API_KEY | API key for Serper.dev search | - |
| log_level | LOG_LEVEL | Logging detail level | INFO |
| max_search_results | MAX_SEARCH_RESULTS | Search results to process | 5 |
| memory_limit | MEMORY_LIMIT | Working memory capacity | 100 |
| output_format | OUTPUT_FORMAT | Results format (markdown, text, html) | markdown |
| timeout | REQUEST_TIMEOUT | Web request timeout (seconds) | 30 |

## Usage

### Basic Research Tasks

1. Create a text file with research questions:
   ```
   # tasks.txt
   Find the name of the COO of the organization that mediated talks between US and Chinese AI companies in Geneva in 2023.
     By what percentage did Volkswagen reduce their Scope 1 and Scope 2 greenhouse gas emissions in 2023 compared to 2021?
   ```

   Note: Empty lines between tasks help the system distinguish between separate questions.

2. Run the research process:
   ```bash
   python main.py tasks.txt
   ```

3. Results will be saved to the `results/` directory as Markdown files.

### Multi-Criteria Research Tasks

For complex queries with multiple requirements:

```
# multi_criteria_tasks.txt
Compile a list of companies satisfying the following criteria:
    They are based in the EU
    They operate within the motor vehicle sector
    Their greenhouse gas emissions are available for 2021-2023
    They earned more than €1B in revenue in 2023
```

The system recognizes this as a single multi-criteria task and adapts its synthesis strategy accordingly.

### Command Line Options

```bash
python main.py tasks.txt --output custom_output_dir
```

| Option | Description | Default |
|--------|-------------|---------|
| task_file | Path to text file containing tasks | (required) |
| --output | Directory to store results | results/ |

## Project Structure

The project structure reflects the enhanced ReAct implementation with dynamic analysis:

- **agent/**: Core reasoning and coordination
  - **agent.py**: Main controller with dynamic task analysis and multi-strategy synthesis
  - **comprehension.py**: Enhanced reasoning with pattern recognition for answer types
  - **memory.py**: Short-term memory for tracking observations and synthesis context
  - **planner.py**: Adaptive planning based on identified information targets
  
- **tools/**: Action components
  - **search.py**: Information retrieval with robust URL resolution
  - **browser.py**: Content extraction with multiple fallback strategies
  - **code_generator.py**: Data analysis when computational tasks are detected
  - **presentation_tool.py**: Task-adaptive result formatting
  - **tool_registry.py**: Tool management system

- **utils/**: Supporting functions
  - **console_ui.py**: Interface components
  - **formatters.py**: Dynamic output structuring
  - **task_parser.py**: Multi-criteria task parsing
  - **criteria_filter.py**: Multi-criteria verification
  - **logger.py**: Detailed reasoning and synthesis tracking

- **config/**: Research environment configuration
  
- **main.py**: Entry point and experiment runner

## Research Implementation Details

### Dynamic Task Analysis System

The system implements pattern recognition to analyze any research question and determine:

1. **Answer Type Detection**: Identifies whether the question expects a factual answer, comparison, list, or comprehensive analysis
2. **Information Target Identification**: Determines what specific information needs to be gathered 
3. **Output Structure Inference**: Predicts the appropriate format for presenting the answer
4. **Synthesis Strategy Selection**: Chooses from four synthesis approaches based on task characteristics

### Multi-Strategy Synthesis Approaches

#### Extract-and-Verify Strategy
Used for factual lookup questions requiring specific information:
- Searches for target information across multiple sources
- Cross-validates findings for accuracy
- Provides direct answers with source verification

#### Aggregate-and-Filter Strategy  
Applied to comparison and analytical questions:
- Collects relevant data points from multiple sources
- Applies filtering criteria to focus on relevant information
- Synthesizes comparative or analytical insights

#### Collect-and-Organize Strategy
Employed for list-building and compilation tasks:
- Systematically gathers items meeting specified criteria
- Organizes findings in structured formats
- Validates completeness of collected information

#### Comprehensive-Synthesis Strategy
Used for complex, multi-faceted research questions:
- Integrates information from diverse sources
- Builds coherent narratives or explanations
- Balances breadth and depth of coverage

### Enhanced Parameter Resolution

The system includes robust handling of web search challenges:
- Multiple URL extraction strategies from search results
- Fallback mechanisms for content retrieval failures
- Validation of information sources and URLs
- Graceful degradation when full content is unavailable

### Entity Extraction & Relationship Mapping

The system extracts relevant entities while maintaining focus on answering the specific question:

- **People**: Names of individuals relevant to the research question
- **Organizations**: Companies, agencies, groups mentioned in sources
- **Roles**: Job titles and positions when relevant to the query
- **Locations**: Geographic information pertinent to the task
- **Dates**: Temporal references important for the research context

Entity extraction supports the synthesis process but does not drive the output format.

### Error Recovery and Robustness

The system implements multiple fallback strategies:

1. **Content Access Failures**: When websites block access, falls back to search snippet analysis
2. **URL Resolution Issues**: Multiple strategies for extracting valid URLs from search results
3. **Information Gaps**: Acknowledges limitations and reports partial findings when complete answers aren't available
4. **Synthesis Failures**: Provides available information even when preferred synthesis strategy fails

### Customization Options

You can modify system behavior through configuration:

```python
from config.config_manager import init_config

config = init_config()
config.update('output_format', 'html')  # Options: markdown, json, html
config.update('max_search_results', 10)  # Increase search breadth
```

## Research Limitations & Observations

As a research implementation, this project provides insights into both capabilities and current limitations:

### Current Research Limitations

1. **Web Access Constraints**: Sites with anti-scraping measures may limit data collection, providing opportunities to study fallback strategies
2. **Complex Query Formulation**: Highly specialized domains sometimes require domain-specific search strategies
3. **Synthesis Boundary Cases**: Edge cases in task analysis provide insights into pattern recognition limitations
4. **Computational Requirements**: Multi-criteria tasks with extensive search requirements demonstrate resource scaling behavior

### Research Insights from Implementation

Detailed logs in the `logs/` directory provide research data on:
- Dynamic task analysis decision patterns
- Synthesis strategy selection effectiveness
- URL resolution fallback frequency and success rates
- Entity extraction accuracy across different content types
- Error recovery mechanism performance

These logs are valuable for understanding the system's behavior and identifying areas for algorithmic improvement.

## Contributing

This research implementation welcomes contributions, particularly in areas of:
- Enhanced pattern recognition for task analysis
- Additional synthesis strategies for specialized question types
- Improved robustness in web content extraction
- Performance optimization for large-scale research tasks

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Research Background & Extensions

This project implements and extends the ReAct (Reasoning + Acting) paradigm from ["ReAct: Synergizing Reasoning and Acting in Language Models"](https://arxiv.org/abs/2210.03629) (Yao et al., 2022).

### Core ReAct Implementation

The foundational ReAct components:
1. **Reasoning**: Task decomposition and solution planning
2. **Acting**: Tool execution based on reasoning
3. **Observation**: Processing action results
4. **Iteration**: Feedback loops for refinement

### Research Extensions

This implementation extends ReAct with:

- **Dynamic Task Analysis**: Pattern recognition for answer type detection without hardcoded rules
- **Multi-Strategy Synthesis**: Adaptive synthesis based on task characteristics rather than fixed approaches  
- **Robust Parameter Resolution**: Multiple fallback mechanisms for real-world web research challenges
- **Task-Focused Output**: Direct answer generation aligned with question intent

### Research Findings

Key observations from this implementation:

1. **Pattern Recognition Effectiveness**: Dynamic task analysis successfully identifies answer types across diverse question structures
2. **Synthesis Strategy Impact**: Different synthesis strategies show measurable differences in answer quality for different question types
3. **Fallback Strategy Value**: Robust parameter resolution significantly improves success rates for web content access
4. **Entity vs. Answer Focus**: Maintaining task focus while extracting entities produces more relevant outputs than entity-driven approaches

### Acknowledgements

This research implementation draws from established agent concepts and development approaches, including:

- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling) - Best practices for tool-using agents
- [Anthropic's Claude Agent Guide](https://www.anthropic.com/research/claude-agent) - Methods for reliable agent construction
- [LangChain ReAct Implementation](https://python.langchain.com/docs/modules/agents/agent_types/react) - Technical approaches for implementing ReAct

### Related Research

- [Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903) - Wei et al. (2022)
- [Language Models as Zero-Shot Planners](https://arxiv.org/abs/2201.07207) - Huang et al. (2022)
- [Faithful Reasoning Using Large Language Models](https://arxiv.org/abs/2208.14271) - Creswell et al. (2022)
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) - Schick et al. (2023)
