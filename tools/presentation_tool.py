from typing import Dict, Any, List, Optional
import re
from .tool_registry import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)

class PresentationTool(BaseTool):
    """Presentation tool focused on clear, relevant answer synthesis."""

    def __init__(self):
        super().__init__(name="present", description="Synthesize and present research results")

    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        params = parameters or {}
        title = params.get("title", "Research Results")
        prompt = params.get("prompt", "") or ""
        results = params.get("results", [])
        suppress_debug = bool(params.get("suppress_debug", False))

        # Extract the research question
        research_question = self._extract_research_question(prompt)
        logger.info(f"Processing research question: {research_question}")
        
        # Collect and validate research content
        research_content = self._collect_research_content(results)
        logger.info(f"Collected {len(research_content)} content items")
        
        # Synthesize answer with clear logic
        synthesized_answer = self._synthesize_answer(research_question, research_content, prompt)
        
        if suppress_debug:
            return {"status": "success", "output": {"final_text": synthesized_answer}}
        else:
            return {"status": "success", "output": {"title": title, "content": synthesized_answer}}

    def _extract_research_question(self, prompt: str) -> str:
        """Extract the core research question with simple, reliable patterns."""
        if not prompt:
            return "Research Question"
        
        # Look for explicit question markers
        patterns = [
            r"answer to:\s*(.+?)(?:\n|$)",
            r"question:\s*(.+?)(?:\n|$)",
            r"find:\s*(.+?)(?:\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE | re.DOTALL)
            if match:
                question = match.group(1).strip()
                # Clean up the question
                question = re.sub(r'\s+', ' ', question)
                return question[:200]  # Reasonable length limit
        
        # Fallback: use first meaningful line
        lines = [line.strip() for line in prompt.split('\n') if line.strip()]
        if lines:
            return lines[0][:200]
        
        return "Research Question"

    def _collect_research_content(self, results: List[Dict]) -> List[Dict]:
        """Collect content with better validation and structure."""
        content_items = []
        
        for i, result in enumerate(results):
            if result.get("status") != "success":
                logger.debug(f"Skipping failed result {i}: {result.get('status')}")
                continue
                
            output = result.get("output", {})
            if not output:
                continue
            
            # Extract content based on type
            content_item = self._extract_content_from_result(output, i + 1)
            if content_item:
                content_items.append(content_item)
        
        return content_items

    def _extract_content_from_result(self, output: Any, step_number: int) -> Optional[Dict]:
        """Extract content from a single result with clear logic."""
        content_item = {
            "step_number": step_number,
            "content": "",
            "url": "",
            "title": "",
            "type": "unknown"
        }
        
        if isinstance(output, dict):
            # Browser/fetch results
            if "extracted_text" in output:
                content_item.update({
                    "content": output["extracted_text"],
                    "url": output.get("url", ""),
                    "title": output.get("title", f"Source {step_number}"),
                    "type": "webpage"
                })
                return content_item if content_item["content"].strip() else None
            
            # Search results
            elif "search_results" in output:
                search_results = output["search_results"]
                if isinstance(search_results, list) and search_results:
                    # Create a summary of search results
                    result_summaries = []
                    for result in search_results[:5]:  # Limit to top 5
                        if isinstance(result, dict):
                            title = result.get("title", "")
                            snippet = result.get("snippet", "")
                            if title and snippet:
                                result_summaries.append(f"{title}: {snippet}")
                    
                    if result_summaries:
                        content_item.update({
                            "content": "\n".join(result_summaries),
                            "title": f"Search Results {step_number}",
                            "type": "search"
                        })
                        return content_item
            
            # Direct text content
            elif "content" in output:
                content_item.update({
                    "content": str(output["content"]),
                    "title": output.get("title", f"Content {step_number}"),
                    "type": "text"
                })
                return content_item if content_item["content"].strip() else None
        
        # Handle string outputs
        elif isinstance(output, str) and output.strip():
            content_item.update({
                "content": output,
                "title": f"Result {step_number}",
                "type": "text"
            })
            return content_item
        
        return None

    def _synthesize_answer(self, question: str, content_items: List[Dict], original_prompt: str) -> str:
        """Main synthesis method with clear question type routing."""
        if not content_items:
            return self._handle_no_content(question)
        
        # Detect question type
        question_type = self._detect_question_type(question)
        logger.info(f"Detected question type: {question_type}")
        
        # Route to appropriate synthesis method
        if question_type == "factual":
            return self._synthesize_factual_answer(question, content_items)
        elif question_type == "quantitative":
            return self._synthesize_quantitative_answer(question, content_items)
        elif question_type == "list":
            return self._synthesize_list_answer(question, content_items)
        elif question_type == "comprehensive":
            return self._synthesize_comprehensive_answer(question, content_items)
        else:
            return self._synthesize_general_answer(question, content_items)

    def _detect_question_type(self, question: str) -> str:
        """Simple, reliable question type detection."""
        question_lower = question.lower()
        
        # Factual questions (who, what, when, where is/are)
        if re.search(r'\b(who|what|when|where)\s+(?:is|are|was|were)\b', question_lower):
            return "factual"
        
        # Quantitative questions (how many, how much, what percentage)
        if re.search(r'\b(how many|how much|what percentage|what number)\b', question_lower):
            return "quantitative"
        
        # List questions (list, compile, find all)
        if re.search(r'\b(list|compile|find all|identify all|what are the)\b', question_lower):
            return "list"
        
        # Comprehensive questions (explain, describe, analyze)
        if re.search(r'\b(explain|describe|analyze|discuss|compare|evaluate)\b', question_lower):
            return "comprehensive"
        
        return "general"

    def _synthesize_factual_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize direct factual answers."""
        logger.debug(f"Synthesizing factual answer for: {question}")
        
        # Look for direct answers in content
        best_answer = self._find_direct_factual_answer(question, content_items)
        if best_answer:
            return best_answer
        
        # Fallback to key facts
        key_facts = self._extract_key_facts(question, content_items, max_facts=3)
        if key_facts:
            answer_parts = [f"Based on the research findings:"]
            answer_parts.extend([f"• {fact['content']}" for fact in key_facts[:2]])
            
            # Add sources
            sources = self._get_unique_sources(key_facts)
            if sources:
                answer_parts.append("\nSources:")
                answer_parts.extend([f"- {source}" for source in sources[:3]])
            
            return "\n".join(answer_parts)
        
        return self._handle_no_relevant_content(question, content_items)

    def _synthesize_quantitative_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize answers for quantitative questions."""
        logger.debug(f"Synthesizing quantitative answer for: {question}")
        
        # Look for numbers and statistics
        numbers_found = []
        
        for item in content_items:
            content = item["content"]
            # Find numbers with context
            number_patterns = [
                r'(\d+(?:\.\d+)?(?:\s*%|\s*percent))',  # Percentages
                r'(\d+(?:,\d{3})*(?:\.\d+)?)',  # Regular numbers
                r'(\$\d+(?:,\d{3})*(?:\.\d+)?)',  # Money
            ]
            
            for pattern in number_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Get context around the number
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end].strip()
                    
                    numbers_found.append({
                        "number": match.group(1),
                        "context": context,
                        "source": item["title"]
                    })
        
        if numbers_found:
            answer_parts = [f"Based on the research findings:"]
            
            # Add the most relevant numbers
            for num_info in numbers_found[:3]:
                answer_parts.append(f"• {num_info['context']}")
            
            # Add sources
            sources = list(set([num_info["source"] for num_info in numbers_found[:3]]))
            if sources:
                answer_parts.append("\nSources:")
                answer_parts.extend([f"- {source}" for source in sources])
            
            return "\n".join(answer_parts)
        
        return self._synthesize_general_answer(question, content_items)

    def _synthesize_list_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize answers for list-type questions."""
        logger.debug(f"Synthesizing list answer for: {question}")
        
        # Extract list items from content
        list_items = []
        
        for item in content_items:
            content = item["content"]
            
            # Look for bullet points, numbered lists, etc.
            list_patterns = [
                r'(?:^|\n)\s*[•\-\*]\s*(.+?)(?=\n|$)',  # Bullet points
                r'(?:^|\n)\s*\d+\.\s*(.+?)(?=\n|$)',    # Numbered lists
                r'(?:^|\n)([A-Z][^.!?]*(?:Inc|Ltd|Corp|Company|Organization)[^.!?]*)\.?', # Company names
            ]
            
            for pattern in list_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    list_item = match.group(1).strip()
                    if len(list_item) > 10 and len(list_item) < 200:  # Reasonable length
                        list_items.append({
                            "item": list_item,
                            "source": item["title"]
                        })
        
        if list_items:
            # Remove duplicates and limit
            unique_items = []
            seen_items = set()
            
            for item_info in list_items:
                item_lower = item_info["item"].lower()
                if item_lower not in seen_items:
                    unique_items.append(item_info)
                    seen_items.add(item_lower)
                    if len(unique_items) >= 10:  # Limit to 10 items
                        break
            
            answer_parts = [f"Based on the research findings, here are the key items:"]
            for i, item_info in enumerate(unique_items, 1):
                answer_parts.append(f"{i}. {item_info['item']}")
            
            # Add sources
            sources = list(set([item_info["source"] for item_info in unique_items]))
            if sources:
                answer_parts.append("\nSources:")
                answer_parts.extend([f"- {source}" for source in sources[:5]])
            
            return "\n".join(answer_parts)
        
        return self._synthesize_general_answer(question, content_items)

    def _synthesize_comprehensive_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize comprehensive answers."""
        logger.debug(f"Synthesizing comprehensive answer for: {question}")
        
        # Extract key themes and organize information
        key_facts = self._extract_key_facts(question, content_items, max_facts=8)
        
        if key_facts:
            # Group facts by theme/source
            answer_parts = [f"Based on the research findings:"]
            
            # Add main findings
            for i, fact in enumerate(key_facts[:6], 1):
                if len(fact["content"]) > 20:  # Only substantial facts
                    answer_parts.append(f"\n{i}. {fact['content']}")
            
            # Add sources
            sources = self._get_unique_sources(key_facts)
            if sources:
                answer_parts.append("\nSources:")
                answer_parts.extend([f"- {source}" for source in sources[:5]])
            
            return "\n".join(answer_parts)
        
        return self._handle_no_relevant_content(question, content_items)

    def _synthesize_general_answer(self, question: str, content_items: List[Dict]) -> str:
        """General synthesis for unclear question types."""
        logger.debug(f"Synthesizing general answer for: {question}")
        
        # Extract most relevant facts
        key_facts = self._extract_key_facts(question, content_items, max_facts=5)
        
        if key_facts:
            answer_parts = [f"Based on the research findings:"]
            
            # Add the most relevant information
            for fact in key_facts[:3]:
                if len(fact["content"]) > 15:
                    answer_parts.append(f"• {fact['content']}")
            
            # Add sources
            sources = self._get_unique_sources(key_facts)
            if sources:
                answer_parts.append("\nSources:")
                answer_parts.extend([f"- {source}" for source in sources[:3]])
            
            return "\n".join(answer_parts)
        
        return self._handle_no_relevant_content(question, content_items)

    def _find_direct_factual_answer(self, question: str, content_items: List[Dict]) -> Optional[str]:
        """Find direct answers for factual questions."""
        question_lower = question.lower()
        question_keywords = self._extract_question_keywords(question)
        
        best_sentence = None
        best_score = 0
        best_source = None
        
        for item in content_items:
            content = self._clean_content_lightly(item["content"])
            sentences = self._split_into_sentences(content)
            
            for sentence in sentences:
                if len(sentence) < 20 or len(sentence) > 300:
                    continue
                
                # Skip navigation sentences
                if self._is_navigation_sentence(sentence):
                    continue
                
                # Score the sentence
                score = self._score_sentence_relevance(sentence, question_keywords)
                
                if score > best_score:
                    best_score = score
                    best_sentence = sentence
                    best_source = item
        
        if best_sentence and best_score >= 2:
            clean_sentence = self._clean_sentence(best_sentence)
            source_text = f"- {best_source['title']}"
            if best_source.get('url'):
                source_text += f" ({best_source['url']})"
            
            return f"Based on the research findings: {clean_sentence}\n\nSource:\n{source_text}"
        
        return None

    def _extract_key_facts(self, question: str, content_items: List[Dict], max_facts: int = 5) -> List[Dict]:
        """Extract key facts relevant to the question."""
        question_keywords = self._extract_question_keywords(question)
        facts = []
        
        for item in content_items:
            content = self._clean_content_lightly(item["content"])
            sentences = self._split_into_sentences(content)
            
            for sentence in sentences:
                if len(sentence) < 20 or len(sentence) > 400:
                    continue
                
                if self._is_navigation_sentence(sentence):
                    continue
                
                score = self._score_sentence_relevance(sentence, question_keywords)
                
                if score > 0:
                    facts.append({
                        "content": self._clean_sentence(sentence),
                        "score": score,
                        "source": item["title"],
                        "url": item.get("url", "")
                    })
        
        # Sort by score and return top facts
        facts.sort(key=lambda x: x["score"], reverse=True)
        return facts[:max_facts]

    def _extract_question_keywords(self, question: str) -> List[str]:
        """Extract meaningful keywords from the question."""
        # Remove common question words
        stop_words = {
            'who', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'about', 'into', 'through', 'during', 'before', 'after'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords

    def _score_sentence_relevance(self, sentence: str, keywords: List[str]) -> int:
        """Score how relevant a sentence is to the question keywords."""
        sentence_lower = sentence.lower()
        score = 0
        
        for keyword in keywords:
            if keyword in sentence_lower:
                # Higher score for longer, more specific keywords
                if len(keyword) > 6:
                    score += 3
                elif len(keyword) > 4:
                    score += 2
                else:
                    score += 1
        
        # Bonus for sentences that look like direct statements
        if re.search(r'\b(is|are|was|were|serves as|known as)\b', sentence_lower):
            score += 1
        
        return score

    def _clean_content_lightly(self, content: str) -> str:
        """Light cleaning that preserves information."""
        if not content:
            return ""
        
        # Remove obvious navigation elements but preserve content
        patterns_to_remove = [
            r'Edit\s+links',
            r'Jump to navigation',
            r'Toggle.*?navigation',
            r'View source',
            r'Print.*?page',
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content)
        return content.strip()

    def _split_into_sentences(self, content: str) -> List[str]:
        """Split content into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', content)
        return [s.strip() for s in sentences if s.strip()]

    def _is_navigation_sentence(self, sentence: str) -> bool:
        """Check if a sentence is navigation/markup."""
        sentence_lower = sentence.lower()
        navigation_indicators = [
            'edit', 'links', 'navigation', 'menu', 'sidebar', 'footer',
            'toggle', 'collapse', 'expand', 'show', 'hide', 'references',
            'external links', 'see also', 'categories', 'wikipedia'
        ]
        
        return any(indicator in sentence_lower for indicator in navigation_indicators)

    def _clean_sentence(self, sentence: str) -> str:
        """Clean a sentence for presentation."""
        # Remove citation markers
        sentence = re.sub(r'\[\d+\]', '', sentence)
        # Clean up whitespace
        sentence = re.sub(r'\s+', ' ', sentence)
        return sentence.strip()

    def _get_unique_sources(self, facts: List[Dict]) -> List[str]:
        """Get unique source descriptions from facts."""
        sources = []
        seen_titles = set()
        
        for fact in facts:
            title = fact.get("source", "")
            if title and title not in seen_titles:
                if fact.get("url"):
                    sources.append(f"{title} ({fact['url']})")
                else:
                    sources.append(title)
                seen_titles.add(title)
        
        return sources

    def _handle_no_content(self, question: str) -> str:
        """Handle cases where no content was found."""
        return f"No research content was available to answer the question: {question}"

    def _handle_no_relevant_content(self, question: str, content_items: List[Dict]) -> str:
        """Handle cases where content exists but isn't relevant."""
        source_count = len(content_items)
        return (f"Based on {source_count} source(s) reviewed, "
                f"no specific information was found to directly answer: {question}")

# Back-compat alias for older imports
PresentTool = PresentationTool
