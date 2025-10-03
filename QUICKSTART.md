# Quick Start Guide

Get up and running with the Web Research Agent in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Gemini API key (free from [Google AI Studio](https://makersuite.google.com/app/apikey))
- Serper API key (free tier from [Serper.dev](https://serper.dev))

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
GEMINI_API_KEY=your_actual_gemini_api_key
SERPER_API_KEY=your_actual_serper_api_key
```

### 3. Verify Setup

Run the setup checker:

```bash
python check_setup.py
```

All checks should pass (✓).

### 4. Run a Simple Test

Test with simple questions:

```bash
python main.py example_simple.txt
```

This will answer basic questions and save results to `results.txt`.

### 5. Run Real Tasks

Process the full task set:

```bash
python main.py tasks.txt
```

## Understanding the Output

### Console Output
- Shows the agent's reasoning process (Thought → Action → Observation)
- Displays the final answer for each task

### Results File (`results.txt`)
- Contains all task descriptions
- Complete answers with sources
- Execution time and step count

### Log Files (`logs/`)
- Detailed execution traces
- Useful for debugging
- Timestamped for each run

## Example: How the Agent Works

Given the task: "Find the capital of France"

```
Thought: I need to search for the capital of France
Action: search
Action Input: {"query": "capital of France"}
Observation: [Search results show Paris is the capital]

Thought: I have found the answer from reliable sources
Final Answer: The capital of France is Paris.
```

## Common Issues & Solutions

### "GEMINI_API_KEY not set"
- Check that `.env` file exists
- Ensure the key doesn't have quotes around it
- Verify the key is valid from Google AI Studio

### "SERPER_API_KEY not set"
- Sign up at serper.dev (free tier available)
- Copy the API key to your `.env` file

### "Module not found" errors
- Run: `pip install -r requirements.txt`
- Ensure you're in the correct directory

### Tasks timeout before completion
- Increase `MAX_ITERATIONS` in `.env` (e.g., 20 or 25)
- Complex tasks may need more reasoning steps

## Tips for Best Results

1. **Clear Tasks**: Write specific, well-defined tasks
2. **Be Patient**: Complex research takes time (2-10 minutes per task)
3. **Check Logs**: If something fails, check `logs/` for details
4. **Adjust Settings**: Tune `.env` parameters for your needs

## What Can the Agent Do?

✓ Search the web for current information  
✓ Read and extract content from web pages  
✓ Download and analyze datasets  
✓ Perform calculations and data processing  
✓ Compile information from multiple sources  
✓ Provide citations and sources  

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Modify `tasks.txt` with your own research questions
- Add custom tools by following the guide in README.md
- Experiment with different model settings in `.env`

## Need Help?

1. Run `python check_setup.py` to verify configuration
2. Check log files in `logs/` directory
3. Use `-v` flag for verbose output: `python main.py tasks.txt -v`
4. Review the [README.md](README.md) for troubleshooting

---

Happy researching! 🔍🤖