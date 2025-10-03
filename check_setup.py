"""
Setup verification script for the Web Research Agent.
Checks that all dependencies and configuration are correct.
"""

import sys
import os


def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check that required packages are installed."""
    print("\nChecking dependencies...")
    required_packages = [
        "google.generativeai",
        "requests",
        "beautifulsoup4",
        "html2text",
        "python-dotenv",
    ]

    missing = []
    for package in required_packages:
        try:
            if package == "python-dotenv":
                __import__("dotenv")
            elif package == "beautifulsoup4":
                __import__("bs4")
            else:
                __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} not found")
            missing.append(package)

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    return True


def check_env_file():
    """Check for .env file and required variables."""
    print("\nChecking configuration...")

    if not os.path.exists(".env"):
        print("❌ .env file not found")
        print("Copy .env.example to .env and add your API keys")
        return False

    print("✓ .env file exists")

    # Try to load and check for required keys
    try:
        from dotenv import load_dotenv

        load_dotenv()

        gemini_key = os.getenv("GEMINI_API_KEY")
        serper_key = os.getenv("SERPER_API_KEY")

        if not gemini_key or gemini_key == "your_gemini_api_key_here":
            print("❌ GEMINI_API_KEY not set in .env")
            return False
        print("✓ GEMINI_API_KEY is set")

        if not serper_key or serper_key == "your_serper_api_key_here":
            print("❌ SERPER_API_KEY not set in .env")
            return False
        print("✓ SERPER_API_KEY is set")

        return True

    except Exception as e:
        print(f"❌ Error loading .env: {e}")
        return False


def check_structure():
    """Check that required files and directories exist."""
    print("\nChecking project structure...")

    required_files = [
        "agent.py",
        "llm.py",
        "config.py",
        "main.py",
        "tools/__init__.py",
        "tools/base.py",
        "tools/search.py",
        "tools/scrape.py",
        "tools/code_executor.py",
        "tools/file_ops.py",
    ]

    missing = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"❌ {file_path} not found")
            missing.append(file_path)

    if missing:
        print(f"\nMissing files: {', '.join(missing)}")
        return False

    return True


def main():
    """Run all checks."""
    print("=" * 60)
    print("Web Research Agent - Setup Verification")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_structure),
        ("Configuration", check_env_file),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = all(result for _, result in results)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("=" * 60)

    if all_passed:
        print("\n✓ All checks passed! You're ready to run the agent.")
        print("\nTry running:")
        print("  python main.py example_simple.txt")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
