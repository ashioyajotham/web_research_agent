
import sys
import json
import urllib.request
import re

def summarize_and_extract(url, task_description):
    """
    This function fetches the content of a URL, and extracts sentences relevant to the task.
    """
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return {"summary": f"Could not fetch content from {url}: {e}", "extracted_info": []}

    # Simple sentence splitting
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', html)

    # Keywords from task description
    task_keywords = [word.lower() for word in task_description.split() if len(word) > 3]

    extracted_info = []
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in task_keywords):
            # Clean up the sentence
            sentence = re.sub(r'<[^>]+>', '', sentence) # Remove HTML tags
            sentence = sentence.strip()
            if sentence:
                extracted_info.append(sentence)

    return {
        "summary": "Extracted relevant sentences.",
        "extracted_info": extracted_info
    }

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python summarizer.py <url> <task_description>")
        sys.exit(1)

    url = sys.argv[1]
    task_description = sys.argv[2]

    result = summarize_and_extract(url, task_description)
    print(json.dumps(result, indent=2))

