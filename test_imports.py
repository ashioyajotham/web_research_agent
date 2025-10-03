import sys

try:
    import google.generativeai as genai

    print("✓ google.generativeai")
except ImportError:
    print("✗ google.generativeai NOT FOUND")
    sys.exit(1)

try:
    import html2text

    print("✓ html2text")
except ImportError:
    print("✗ html2text NOT FOUND")
    sys.exit(1)

try:
    import requests

    print("✓ requests")
except ImportError:
    print("✗ requests NOT FOUND")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup

    print("✓ beautifulsoup4")
except ImportError:
    print("✗ beautifulsoup4 NOT FOUND")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    print("✓ python-dotenv")
except ImportError:
    print("✗ python-dotenv NOT FOUND")
    sys.exit(1)

print("\nAll required packages are installed!")
