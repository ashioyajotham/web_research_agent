from setuptools import setup, find_packages

setup(
    name="web-research-agent",
    version="1.1.10",
    packages=find_packages(),
    include_package_data=True,
    py_modules=["cli"],
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
        "html2text>=2020.1.16",
        "google-generativeai>=0.3.0",
        "python-dotenv>=0.19.0",
        "prompt_toolkit>=3.0.0",
        "rich>=10.0.0",
        "keyring>=23.0.0"
    ],
    entry_points={
        'console_scripts': [
            'web-research=cli:main',
        ],
    },
    author="Victor Jotham Ashioya",
    author_email="victorashioya960@gmail.com",
    description="An AI agent for web research, capable of understanding complex tasks and executing them using various tools.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ashioyajotham/web_research_agent",
    project_urls={
        "Bug Tracker": "https://github.com/ashioyajotham/web_research_agent/issues",
        "Documentation": "https://github.com/ashioyajotham/web_research_agent#readme",
        "Source Code": "https://github.com/ashioyajotham/web_research_agent",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai, research, web, agent, search",
    python_requires=">=3.9",
)
