# Installing Web Research Agent

## From PyPI (Recommended)

```bash
pip install web-research-agent
```

After installation, you can run the tool with:

```bash
web-research --help
```

## Configuration

After installation, set up your API keys:

```bash
web-research config --api-key="your_gemini_api_key" --serper-key="your_serper_api_key"
```

## From Source

If you prefer to install from source:

```bash
git clone https://github.com/ashioyajotham/web-research-agent.git
cd web-research-agent
pip install -e .
