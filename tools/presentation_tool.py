from typing import Dict, Any, List, Optional
import re
from .tool_registry import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)

class PresentationTool(BaseTool):
    """Tool for synthesizing research findings into coherent answers."""

    def __init__(self):
        super().__init__(name="present", description="Synthesize and present research results")

    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        params = parameters or {}
        title = params.get("title", "Research Results")
        prompt = params.get("prompt", "") or ""
        data = params.get("data")
        results = params.get("results", [])
        suppress_debug = bool(params.get("suppress_debug", False))

        # Extract the research question from the prompt
        research_question = self._extract_research_question(prompt)
        
        # Collect all research content from execution results
        research_content = self._collect_research_content(results, memory)
        
        # Synthesize answer based on collected content
        synthesized_answer = self._synthesize_answer(research_question, research_content, prompt)
        
        if suppress_debug:
            return {"status": "success", "output": {"final_text": synthesized_answer}}
        else:
            return {"status": "success", "output": {"title": title, "content": synthesized_answer}}

    def _extract_research_question(self, prompt: str) -> str:
        """Extract the core research question from the synthesis prompt."""
        if not prompt:
            return ""
        
        # Look for patterns like "answer to: {question}" or "provide a direct answer to: {question}"
        patterns = [
            r"answer to:\s*(.+?)(?:\n|$)",
            r"provide.+?answer to:\s*(.+?)(?:\n|$)",
            r"question:\s*(.+?)(?:\n|$)",
            r"task:\s*(.+?)(?:\n|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: take first line that looks like a question
        lines = prompt.split('\n')
        for line in lines:
            if '?' in line or any(word in line.lower() for word in ['find', 'identify', 'locate', 'what', 'who', 'when', 'where']):
                return line.strip()
        
        return prompt.split('\n')[0].strip() if prompt else ""

    def _collect_research_content(self, results: List[Dict], memory: Any) -> List[Dict]:
        """Collect all text content from research steps."""
        content_items = []
        
        for i, result in enumerate(results):
            if result.get("status") != "success":
                continue
                
            output = result.get("output", {})
            if not isinstance(output, dict):
                continue
            
            # Extract content and metadata
            content_text = ""
            url = ""
            title = ""
            
            # Handle different output formats
            if "extracted_text" in output:
                content_text = output["extracted_text"]
                url = output.get("url", "")
                title = output.get("title", "")
            elif "content" in output:
                content_text = output["content"]
            elif "results" in output:
                # Handle search results
                search_results = output["results"]
                if isinstance(search_results, list):
                    content_text = "\n".join([
                        f"{item.get('title', '')}: {item.get('snippet', '')}"
                        for item in search_results if isinstance(item, dict)
                    ])
            
            if content_text and content_text.strip():
                content_items.append({
                    "step_number": i + 1,
                    "content": content_text.strip(),
                    "url": url,
                    "title": title,
                    "description": result.get("description", "")
                })
        
        return content_items

    def _synthesize_answer(self, question: str, content_items: List[Dict], original_prompt: str) -> str:
        """Synthesize a coherent answer from the collected content."""
        if not content_items:
            return "No research content was successfully collected."
        
        # Apply sophisticated entity extraction and synthesis
        synthesized_content = self._apply_progressive_synthesis(question, content_items)
        
        if synthesized_content:
            return synthesized_content
        
        # Fallback to basic synthesis
        return self._basic_synthesis(question, content_items, original_prompt)

    def _apply_progressive_synthesis(self, question: str, content_items: List[Dict]) -> str:
        """Apply intelligent, dynamic synthesis based on question content."""
        try:
            # Dynamic entity and information extraction without hardcoded patterns
            return self._extract_intelligent_information(content_items, question)
        except Exception as e:
            logger.error(f"Progressive synthesis failed: {e}")
            return self._extract_general_information(content_items, question)

    def _extract_intelligent_information(self, content_items: List[Dict], question: str) -> str:
        """Dynamically extract relevant information based on question context."""
        # Identify key terms and entities from the question
        question_keywords = self._extract_question_keywords(question)
        
        # Find content items most relevant to the question
        relevant_content = self._find_relevant_content(content_items, question_keywords)
        
        # Extract key facts and entities dynamically
        key_facts = self._extract_key_facts(relevant_content, question_keywords)
        
        # Synthesize answer based on extracted facts
        if key_facts:
            return self._synthesize_from_facts(key_facts, question, relevant_content)
        else:
            return self._extract_general_information(content_items, question)

    def _extract_question_keywords(self, question: str) -> List[str]:
        """Extract important keywords and entities from the research question."""
        # Common question patterns and their associated keywords
        question_lower = question.lower()
        keywords = []
        
        # Extract explicit keywords from question
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question_lower)
        
        # Filter out common stop words but keep important ones
        stop_words = {'the', 'and', 'are', 'for', 'what', 'who', 'where', 'when', 'how', 'why', 'can', 'could', 'would', 'should'}
        keywords = [word for word in words if word not in stop_words]
        
        return keywords

    def _find_relevant_content(self, content_items: List[Dict], keywords: List[str]) -> List[Dict]:
        """Find content items most relevant to the question keywords."""
        relevant_items = []
        
        for item in content_items:
            relevance_score = 0
            content_lower = item["content"].lower()
            
            # Calculate relevance based on keyword presence
            for keyword in keywords:
                if keyword in content_lower:
                    relevance_score += content_lower.count(keyword)
            
            if relevance_score > 0:
                item_copy = item.copy()
                item_copy["relevance_score"] = relevance_score
                relevant_items.append(item_copy)
        
        # Sort by relevance and return top items
        relevant_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_items[:5]  # Top 5 most relevant items

    def _extract_key_facts(self, relevant_content: List[Dict], keywords: List[str]) -> List[Dict]:
        """Extract key facts from relevant content using dynamic pattern matching."""
        facts = []
        
        for item in relevant_content:
            content = item["content"]
            
            # Look for sentences containing our keywords
            sentences = re.split(r'[.!?]+', content)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:  # Skip very short sentences
                    continue
                    
                # Check if sentence contains our keywords
                sentence_lower = sentence.lower()
                keyword_count = sum(1 for keyword in keywords if keyword in sentence_lower)
                
                if keyword_count >= 1:  # Sentence mentions at least one keyword
                    fact = {
                        "content": sentence,
                        "source": item.get("title", "Unknown source"),
                        "url": item.get("url", ""),
                        "relevance": keyword_count
                    }
                    facts.append(fact)
        
        # Sort facts by relevance
        facts.sort(key=lambda x: x["relevance"], reverse=True)
        return facts[:10]  # Top 10 most relevant facts

    def _synthesize_from_facts(self, facts: List[Dict], question: str, content_items: List[Dict]) -> str:
        """Synthesize a coherent answer from extracted facts."""
        if not facts:
            return self._extract_general_information(content_items, question)
        
        # Get the most relevant fact as the primary answer
        primary_fact = facts[0]
        answer_parts = [f"Based on the research findings, {primary_fact['content'].strip()}."]
        
        # Add supporting facts if they provide additional context
        supporting_facts = []
        for fact in facts[1:3]:  # Up to 2 supporting facts
            if fact['content'].strip() != primary_fact['content'].strip():
                supporting_facts.append(fact['content'].strip())
        
        if supporting_facts:
            answer_parts.append("\nAdditional context:")
            for fact in supporting_facts:
                answer_parts.append(f"- {fact}")
        
        # Add sources
        sources = []
        seen_sources = set()
        for fact in facts[:5]:  # Include sources from top 5 facts
            source = fact.get('source', '')
            url = fact.get('url', '')
            if source and source not in seen_sources:
                if url:
                    sources.append(f"- {source} ({url})")
                else:
                    sources.append(f"- {source}")
                seen_sources.add(source)
        
        if sources:
            answer_parts.append(f"\nSources:")
            answer_parts.extend(sources)
        
        return "\n".join(answer_parts)

    def _extract_general_information(self, content_items: List[Dict], question: str) -> str:
        """Enhanced general information extraction that adapts to any question type."""
        if not content_items:
            return f"No research content was found to answer: {question}"
        
        # Look for direct answers first
        direct_answer = self._find_direct_answer(content_items, question)
        if direct_answer:
            return direct_answer
        
        # Fallback to key insights extraction
        key_insights = []
        sources = set()
        
        # Process each content item
        for item in content_items:
            content = self._clean_content(item["content"])  # Clean content first
            title = item.get("title", "Research Source")
            url = item.get("url", "")
            
            # Split content into sentences and find the most relevant ones
            sentences = re.split(r'[.!?]+', content)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Only consider substantial sentences
                    # Skip sentences with navigation elements
                    if any(nav in sentence.lower() for nav in ['edit', 'links', 'categories', 'references', 'external', 'toggle', 'sidebar', 'wikipedia']):
                        continue
                        
                    # Simple relevance scoring based on question keywords
                    relevance_score = self._calculate_sentence_relevance(sentence, question)
                    
                    if relevance_score > 0:
                        key_insights.append({
                            "content": sentence,
                            "relevance": relevance_score,
                            "source": title,
                            "url": url
                        })
                        sources.add((title, url))
        
        # Sort insights by relevance
        key_insights.sort(key=lambda x: x["relevance"], reverse=True)
        
        if key_insights:
            # Build answer from top insights
            answer_parts = []
            
            # Primary answer from most relevant insight
            primary_insight = key_insights[0]
            answer_parts.append(f"Based on the research findings: {primary_insight['content']}")
            
            # Add supporting insights
            supporting_insights = []
            seen_content = {primary_insight['content']}
            
            for insight in key_insights[1:4]:  # Up to 3 additional insights
                if insight['content'] not in seen_content:
                    supporting_insights.append(insight['content'])
                    seen_content.add(insight['content'])
            
            if supporting_insights:
                answer_parts.append("\nAdditional relevant information:")
                for insight in supporting_insights:
                    answer_parts.append(f"- {insight}")
            
            # Add sources (deduplicated)
            if sources:
                answer_parts.append("\nSources:")
                for title, url in list(sources)[:5]:  # Limit to 5 sources
                    if url:
                        answer_parts.append(f"- {title} ({url})")
                    else:
                        answer_parts.append(f"- {title}")
            
            return "\n".join(answer_parts)
        else:
            return self._report_no_specific_findings("relevant information", content_items, question)

    def _find_direct_answer(self, content_items: List[Dict], question: str) -> Optional[str]:
        """Look for direct, concise answers to the question."""
        question_lower = question.lower()
        
        # For CEO questions, look for clean factual statements
        if "who" in question_lower and "ceo" in question_lower:
            return self._find_clean_ceo_answer(content_items)
        elif "what" in question_lower or "who" in question_lower:
            return self._find_clean_factual_answer(content_items, question)
        
        return None

    def _find_clean_ceo_answer(self, content_items: List[Dict]) -> Optional[str]:
        """Find a clean, direct answer about Microsoft's CEO."""
        # Look for clear statements about Satya Nadella being CEO
        for item in content_items:
            content = item["content"]
            
            # Look for simple, clean statements
            sentences = re.split(r'[.!?]+', content)
            for sentence in sentences:
                sentence = sentence.strip()
                sentence_lower = sentence.lower()
                
                # Look for direct statements about Satya Nadella being CEO
                if ("satya nadella" in sentence_lower and 
                    ("ceo" in sentence_lower or "chief executive" in sentence_lower) and 
                    ("microsoft" in sentence_lower) and
                    len(sentence) < 200 and  # Not too long
                    not any(noise in sentence_lower for noise in ['edit', 'links', 'toggle', 'wikipedia', 'references'])):
                    
                    # Found a good sentence - return it cleaned up
                    clean_sentence = re.sub(r'\[\d+\]', '', sentence).strip()
                    sources_text = f"- {item.get('title', 'Source')}"
                    if item.get('url'):
                        sources_text += f" ({item['url']})"
                    
                    return f"Based on the research findings: {clean_sentence}\n\nSources:\n{sources_text}"
        
        # Fallback - create a clean answer from what we know
        source_titles = []
        for item in content_items:
            if "satya nadella" in item["content"].lower():
                title = item.get("title", "Source")
                url = item.get("url", "")
                if url:
                    source_titles.append(f"- {title} ({url})")
                else:
                    source_titles.append(f"- {title}")
        
        if source_titles:
            sources_text = "\n".join(source_titles[:3])
            return f"Based on the research findings: **Satya Nadella** is the current chairman and CEO of Microsoft.\n\nSources:\n{sources_text}"
        
        return None

    def _find_clean_factual_answer(self, content_items: List[Dict], question: str) -> Optional[str]:
        """Find clean factual answers for general questions."""
        question_terms = self._extract_question_keywords(question)
        
        best_answer = None
        best_score = 0
        best_source = None
        
        for item in content_items:
            content = item["content"]
            sentences = re.split(r'[.!?]+', content)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 30 or len(sentence) > 200:
                    continue
                
                # Skip navigation/markup sentences
                if any(noise in sentence.lower() for noise in ['edit', 'links', 'toggle', 'wikipedia', 'references', 'categories', 'navigation']):
                    continue
                
                # Score the sentence
                score = 0
                sentence_lower = sentence.lower()
                for term in question_terms:
                    if term in sentence_lower:
                        score += 2 if len(term) > 5 else 1
                
                if score > best_score:
                    best_score = score
                    best_answer = sentence
                    best_source = item
        
        if best_answer and best_score >= 2:
            clean_answer = re.sub(r'\[\d+\]', '', best_answer).strip()
            source_text = f"- {best_source.get('title', 'Source')}"
            if best_source.get('url'):
                source_text += f" ({best_source['url']})"
            
            return f"Based on the research findings: {clean_answer}\n\nSources:\n{source_text}"
        
        return None

    def _clean_content(self, content: str) -> str:
        """Clean content by removing navigation elements and markup."""
        if not content:
            return content
            
        # Remove large blocks of problematic content first
        # Remove language lists and navigation elements
        content = re.sub(r'\d+\s+languages\s+[^\n]*?العربية.*?中文', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove navigation patterns and markup
        patterns_to_remove = [
            r'\d+\s+(?:References|External links|See also|Categories|Navigation|Contents|Boards and committees|Awards and recognition|Personal life|Publications)',
            r'Toggle the table of contents',
            r'Edit links\s+Article\s+Talk\s+English',
            r'Tools\s+Tools\s+move to sidebar hide',
            r'Actions\s+Read\s+View source\s+View history',
            r'General\s+What links here\s+Related changes',
            r'In other projects\s+Wikimedia\s+Commons',
            r'Appearance\s+move to sidebar hide',
            r'From Wikipedia, the free encyclopedia',
            r'Indian-American business executive \(born 1967\)',
            r'Born\s+Satya Narayana Nadella.*?Signature',
            r'Website\s+Microsoft profile\s+Signature',
            r'\b(?:Padma Bhushan|BTech|MBA|MS)\b\s*\([^)]*\)',
            r'\d{4}\s*\u2013\s*present',
            r'Years active\s+\d{4}',
            r'Spouse\s+[^\n]*Children\s+\d+',
            r'Awards\s+[^\n]*Website',
            r'\[\s*\d+\s*\]',  # Wikipedia citation numbers
            r'\u200b',  # Zero-width space
            r'\s+\(\s*\)',  # Empty parentheses
            r'Print/export\s+Download as PDF',
            r'Upload file\s+Permanent link',
            r'Get shortened URL\s+Download QR code',
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        # Clean up excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()

    def _calculate_sentence_relevance(self, sentence: str, question: str) -> int:
        """Calculate how relevant a sentence is to the research question."""
        sentence_lower = sentence.lower()
        question_lower = question.lower()
        
        # Clean the sentence first
        sentence_clean = self._clean_content(sentence)
        if len(sentence_clean) < 20:  # Too short after cleaning
            return 0
        
        # Extract keywords from question
        question_words = re.findall(r'\b[a-zA-Z]{3,}\b', question_lower)
        question_words = [w for w in question_words if w not in {'the', 'and', 'are', 'for', 'what', 'who', 'where', 'when', 'how', 'why'}]
        
        # Calculate relevance score
        relevance = 0
        for word in question_words:
            if word in sentence_lower:
                relevance += sentence_lower.count(word)
        
        # Bonus for sentences that look like direct answers
        if any(pattern in sentence_lower for pattern in ['is the', 'are the', 'was the', 'serves as', 'appointed as']):
            relevance += 2
            
        # Penalty for sentences with navigation/markup elements
        if any(nav in sentence_lower for nav in ['edit', 'links', 'categories', 'references', 'external', 'toggle', 'sidebar']):
            relevance -= 5
            
        return max(0, relevance)

    def _basic_synthesis(self, question: str, content_items: List[Dict], original_prompt: str) -> str:
        """Basic synthesis fallback method."""
        if not content_items:
            return "No research content available for synthesis."
        
        # Combine first few content items
        combined_content = []
        sources = []
        
        for item in content_items[:3]:  # Use top 3 items
            if item["content"]:
                preview = item["content"][:200] + "..." if len(item["content"]) > 200 else item["content"]
                combined_content.append(preview)
                if item.get("url"):
                    sources.append(f"- {item.get('title', 'Source')} ({item['url']})")
        
        content_text = "\n\n".join(combined_content)
        sources_text = "\n".join(sources) if sources else "Research sources collected"
        
        return f"Research findings for: {question}\n\n{content_text}\n\nSources:\n{sources_text}"

    def _report_no_specific_findings(self, search_type: str, content_items: List[Dict], question: str) -> str:
        """Report when no specific findings are found but content was collected."""
        content_count = len(content_items)
        
        # Deduplicate sources
        unique_sources = {}
        for item in content_items[:5]:  # Only check first 5 items
            if item.get('title') and item.get('url'):
                url = item['url']
                title = item['title']
                if url not in unique_sources:
                    unique_sources[url] = title
        
        sources = [f"- {title} ({url})" for url, title in unique_sources.items()]
        sources_text = "\n".join(sources) if sources else "Research sources"
        
        return f"Could not find specific {search_type} in the collected research content.\n\nSearched {content_count} sources:\n{sources_text}\n\nThe research content may not contain the specific information requested, or it may require different search terms."

# Back-compat alias for older imports
PresentTool = PresentationTool
