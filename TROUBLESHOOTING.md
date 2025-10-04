# Troubleshooting Guide

Common issues and solutions for Web Research Agent.

## Installation Issues

### `'webresearch' is not recognized` (Windows)

**Problem**: After installing with `pip install web-research-agent`, the `webresearch` command doesn't work.

**Cause**: The Python Scripts directory is not in your PATH.

**Solutions**:

#### Quick Fix (No Admin Rights)
```bash
python -m cli
```

#### Permanent Fix - Option 1 (Automated)
1. Open PowerShell as Administrator
2. Navigate to the installation directory
3. Run:
```powershell
.\setup_path.ps1
```

#### Permanent Fix - Option 2 (Manual)
1. Open PowerShell as Administrator
2. Run:
```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:APPDATA\Python\Python313\Scripts",
    "User"
)
```
3. Restart your terminal
4. Try `webresearch` again

#### Temporary Fix (Current Session)
```powershell
$env:Path += ";$env:APPDATA\Python\Python313\Scripts"
webresearch
```

**Note**: Replace `Python313` with your Python version (e.g., `Python312`, `Python311`)

---

### Command not found (Linux/Mac)

**Problem**: `webresearch: command not found`

**Solution**:

#### Option 1 (Automated)
```bash
bash setup_path.sh
source ~/.bashrc  # or ~/.zshrc for zsh
```

#### Option 2 (Manual)
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

---

### Module not found errors

**Problem**: `ModuleNotFoundError: No module named 'X'`

**Solution**:
```bash
pip install --upgrade web-research-agent
```

Or reinstall dependencies:
```bash
pip install google-generativeai requests beautifulsoup4 html2text python-dotenv colorama
```

---

## Configuration Issues

### API Key Errors

**Problem**: `ValueError: GEMINI_API_KEY environment variable is required`

**Solutions**:

1. **Interactive Setup**: Just run `webresearch` and follow the prompts
2. **Manual Setup**: Create `~/.webresearch/config.env` with:
```
GEMINI_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
```

3. **Development Mode**: Create `.env` in project root with the same content

---

### Invalid API Keys

**Problem**: Authentication errors or "Invalid API key"

**Solutions**:

1. **Verify your keys are correct**:
   - Gemini: https://makersuite.google.com/app/apikey
   - Serper: https://serper.dev

2. **Check for extra spaces**: Keys shouldn't have quotes or spaces
   ```
   GEMINI_API_KEY=AIzaSy...  ✓ Good
   GEMINI_API_KEY="AIzaSy..."  ✗ Bad (has quotes)
   GEMINI_API_KEY= AIzaSy...  ✗ Bad (has space)
   ```

3. **Reconfigure**: Run `webresearch` → Option 4 → Re-enter keys

---

## Runtime Issues

### Task Timeout

**Problem**: "Max iterations reached without final answer"

**Solutions**:

1. **Increase iteration limit** in `~/.webresearch/config.env`:
```
MAX_ITERATIONS=25
```

2. **Simplify the task**: Break complex queries into smaller parts

3. **Check logs**: Run with verbose mode to see what's happening
```bash
python main.py tasks.txt -v
```

---

### Network Errors

**Problem**: `Connection timeout`, `Failed to fetch URL`

**Solutions**:

1. **Check internet connection**
2. **Increase timeout** in config:
```
WEB_REQUEST_TIMEOUT=60
```

3. **Check if website blocks bots**: Some sites may block automated requests
4. **Use VPN**: If region-blocked

---

### Empty Results

**Problem**: Agent completes but returns no useful information

**Solutions**:

1. **Check logs**: Look in `logs/` directory for detailed error messages
2. **Verify API keys**: Make sure both Gemini and Serper keys work
3. **Test simple query**: Try `What is the capital of France?`
4. **Check rate limits**: 
   - Serper: 2,500 searches/month (free tier)
   - Gemini: 60 requests/minute (free tier)

---

### Code Execution Errors

**Problem**: "Code execution timed out" or "Error executing code"

**Solutions**:

1. **Increase timeout**:
```
CODE_EXECUTION_TIMEOUT=120
```

2. **Check Python installation**: Ensure Python is in PATH
3. **Install required packages**: The agent needs standard libraries

---

## Performance Issues

### Slow Execution

**Problem**: Tasks take too long to complete

**Solutions**:

1. **Use faster model** (already default):
```
MODEL_NAME=gemini-2.0-flash-exp
```

2. **Reduce output length**:
```
MAX_TOOL_OUTPUT_LENGTH=3000
```

3. **Lower temperature** for more focused responses:
```
TEMPERATURE=0.0
```

---

### High Memory Usage

**Problem**: Agent uses too much memory

**Solutions**:

1. **Reduce context size**:
```
MAX_TOOL_OUTPUT_LENGTH=2000
```

2. **Process tasks one at a time**: Don't run multiple instances

---

## Platform-Specific Issues

### Windows: UnicodeDecodeError

**Problem**: Encoding errors when reading files

**Solution**: Files should be UTF-8 encoded. Check your text editor settings.

---

### Mac: Permission Denied

**Problem**: Can't write to config directory

**Solution**:
```bash
chmod 755 ~/.webresearch
```

---

### Linux: SSL Certificate Error

**Problem**: `[SSL: CERTIFICATE_VERIFY_FAILED]`

**Solution**:
```bash
pip install --upgrade certifi
```

---

## Getting Help

### Enable Verbose Logging

For detailed debugging information:
```bash
python main.py tasks.txt -v
```

### Check Log Files

Logs are saved in `logs/agent_<timestamp>.log`. Look for ERROR or WARNING messages.

### View Recent Logs (Interactive Mode)

1. Run `webresearch`
2. Choose option 3: "View recent logs"

---

## Still Having Issues?

1. **Check requirements**: Python 3.8+ required
2. **Reinstall**: 
   ```bash
   pip uninstall web-research-agent
   pip install --upgrade web-research-agent
   ```

3. **Report a bug**: 
   - GitHub Issues: https://github.com/ashioyajotham/web_research_agent/issues
   - Include: Python version, OS, error message, log excerpt

---

## Quick Diagnostics

Run these commands to gather diagnostic info:

```bash
# Check Python version
python --version

# Check installation
pip show web-research-agent

# Check PATH (Windows)
echo $env:Path

# Check PATH (Linux/Mac)
echo $PATH

# Test imports
python -c "import cli; print('OK')"

# Check config
cat ~/.webresearch/config.env  # Linux/Mac
type %USERPROFILE%\.webresearch\config.env  # Windows
```

---

**Last Updated**: 2025-01-10
**Version**: 1.2.0