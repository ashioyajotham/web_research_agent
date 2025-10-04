"""
Setup configuration for Web Research Agent.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
requirements = []
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="web-research-agent",
    version="1.2.0",
    author="Victor Jotham Ashioya",
    author_email="victorashioya960@gmail.com",
    description="An AI agent using ReAct methodology for autonomous web research tasks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/victorashioya/web_research_agent",
    project_urls={
        "Bug Tracker": "https://github.com/victorashioya/web_research_agent/issues",
        "Documentation": "https://github.com/victorashioya/web_research_agent#readme",
        "Source Code": "https://github.com/victorashioya/web_research_agent",
        "Changelog": "https://github.com/victorashioya/web_research_agent/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "webresearch=cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Natural Language :: English",
    ],
    keywords=[
        "ai",
        "agent",
        "research",
        "web-scraping",
        "llm",
        "gemini",
        "react",
        "autonomous-agent",
        "web-research",
        "information-retrieval",
    ],
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)
