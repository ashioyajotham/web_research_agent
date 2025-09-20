from typing import Dict, Any, List, Optional
import re
from .tool_registry import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)

class ImprovedPresentationTool(BaseTool):
    """Simplified presentation tool focused on clear, relevant answer synthesis."""

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
                    "type": "web_content"
                })
            # Search results
            elif "results" in output and isinstance(output["results"], list):
                search_results = output["results"][:5]  # Limit to top 5
                combined_snippets = []
                for result in search_results:
                    if isinstance(result, dict) and "snippet" in result:
                        title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        if snippet:
                            combined_snippets.append(f"{title}: {snippet}")
                
                if combined_snippets:
                    content_item.update({
                        "content": "\n".join(combined_snippets),
                        "title": f"Search Results (Step {step_number})",
                        "type": "search_results"
                    })
            # Generic content
            elif "content" in output:
                content_item.update({
                    "content": str(output["content"]),
                    "title": output.get("title", f"Content {step_number}"),
                    "type": "generic"
                })
                
        elif isinstance(output, str) and output.strip():
            content_item.update({
                "content": output,
                "title": f"Text Result {step_number}",
                "type": "text"
            })
        
        # Only return if we have meaningful content
        if content_item["content"] and len(content_item["content"].strip()) > 20:
            return content_item
        
        return None

    def _synthesize_answer(self, question: str, content_items: List[Dict], original_prompt: str) -> str:
        """Synthesize answer with clear, debuggable logic."""
        if not content_items:
            return f"No research content was found to answer the question: {question}"
        
        logger.info(f"Synthesizing answer for: {question}")
        logger.info(f"Using {len(content_items)} content items")
        
        # Determine question type for synthesis strategy
        question_type = self._determine_question_type(question)
        logger.info(f"Detected question type: {question_type}")
        
        # Apply appropriate synthesis strategy
        if question_type in ["who", "what", "when", "where"]:
            return self._synthesize_factual_answer(question, content_items)
        elif question_type in ["how_many", "percentage", "number"]:
            return self._synthesize_quantitative_answer(question, content_items)
        elif question_type in ["list", "compile", "multiple"]:
            return self._synthesize_list_answer(question, content_items)
        else:
            return self._synthesize_comprehensive_answer(question, content_items)

    def _determine_question_type(self, question: str) -> str:
        """Determine question type with simple, reliable patterns."""
        question_lower = question.lower()
        
        # Direct pattern matching
        patterns = {
            "who": [r'\bwho\s+is\b', r'\bwho\s+are\b', r'\bwho\s+was\b'],
            "what": [r'\bwhat\s+is\b', r'\bwhat\s+are\b', r'\bwhat\s+was\b'],
            "when": [r'\bwhen\s+', r'\bwhat\s+date\b', r'\bwhat\s+year\b'],
            "where": [r'\bwhere\s+', r'\bwhat\s+location\b'],
            "how_many": [r'\bhow\s+many\b', r'\bnumber\s+of\b'],
            "percentage": [r'\bpercentage\b', r'\bpercent\b', r'\b%\b'],
            "list": [r'\blist\s+of\b', r'\bcompile\b', r'\bidentify\s+all\b'],
        }
        
        for q_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, question_lower):
                    return q_type
        
        return "general"

    def _synthesize_factual_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize direct factual answers."""
        # Extract key terms from question
        key_terms = self._extract_key_terms(question)
        logger.info(f"Key terms: {key_terms}")
        
        # Find most relevant content
        best_content = self._find_most_relevant_content(content_items, key_terms)
        
        if not best_content:
            return self._create_fallback_answer(question, content_items)
        
        # Extract specific answer from content
        answer_sentences = self._extract_answer_sentences(best_content, key_terms)
        
        if answer_sentences:
            primary_answer = answer_sentences[0]
            sources = self._format_sources([best_content])
            
            return f"Based on the research: {primary_answer}\n\n{sources}"
        
        return self._create_fallback_answer(question, content_items)

    def _synthesize_quantitative_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize answers for quantitative questions."""
        # Look for numbers, percentages, quantities
        number_pattern = r'(\d+(?:\.\d+)?)\s*(%|percent|percentage|billion|million|thousand)?'
        
        found_numbers = []
        for item in content_items:
            content = item["content"]
            matches = re.finditer(number_pattern, content, re.IGNORECASE)
            for match in matches:
                context_start = max(0, match.start() - 50)
                context_end = min(len(content), match.end() + 50)
                context = content[context_start:context_end]
                found_numbers.append({
                    "number": match.group(0),
                    "context": context,
                    "source": item["title"]
                })
        
        if found_numbers:
            # Return the most relevant number with context
            best_number = found_numbers[0]  # Could add relevance scoring here
            sources = self._format_sources([{"title": best_number["source"], "url": ""}])
            
            return f"Based on the research: {best_number['context']}\n\n{sources}"
        
        return self._create_fallback_answer(question, content_items)

    def _synthesize_list_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize answers for list-type questions."""
        # For list questions, compile information from all sources
        combined_content = []
        sources = []
        
        for item in content_items:
            if item["content"]:
                # Clean and structure content
                content = self._clean_content_lightly(item["content"])
                combined_content.append(f"From {item['title']}:\n{content}")
                sources.append(item)
        
        if combined_content:
            answer = f"Based on research from multiple sources:\n\n"
            answer += "\n\n".join(combined_content[:3])  # Limit to top 3 sources
            answer += f"\n\n{self._format_sources(sources)}"
            return answer
        
        return self._create_fallback_answer(question, content_items)

    def _synthesize_comprehensive_answer(self, question: str, content_items: List[Dict]) -> str:
        """Synthesize comprehensive answers for complex questions."""
        # Extract key insights from each source
        insights = []
        sources = []
        
        for item in content_items:
            content = self._clean_content_lightly(item["content"])
            if len(content) > 50:  # Only meaningful content
                # Take first few sentences as insight
                sentences = re.split(r'[.!?]+', content)
                insight = '. '.join(sentences[:2]).strip()
                if insight and len(insight) > 30:
                    insights.append(insight + ".")
                    sources.append(item)
        
        if insights:
            answer = f"Research findings for: {question}\n\n"
            for i, insight in enumerate(insights[:3], 1):
                answer += f"{i}. {insight}\n\n"
            answer += self._format_sources(sources)
            return answer
        
        return self._create_fallback_answer(question, content_items)

    def _extract_key_terms(self, question: str) -> List[str]:
        """Extract key terms from question with simple logic."""
        # Remove common question words
        stop_words = {
            'what', 'who', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were',
            'the', 'a', 'an', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'to'
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
        key_terms = [word for word in words if word not in stop_words]
        
        # Return top 5 terms
        return key_terms[:5]

    def _find_most_relevant_content(self, content_items: List[Dict], key_terms: List[str]) -> Optional[Dict]:
        """Find the most relevant content item."""
        if not content_items or not key_terms:
            return content_items[0] if content_items else None
        
        best_item = None
        best_score = 0
        
        for item in content_items:
            content_lower = item["content"].lower()
            score = sum(1 for term in key_terms if term in content_lower)
            
            if score > best_score:
                best_score = score
                best_item = item
        
        return best_item if best_score > 0 else content_items[0]

    def _extract_answer_sentences(self, content_item: Dict, key_terms: List[str]) -> List[str]:
        """Extract sentences that likely contain the answer."""
        content = content_item["content"]
        sentences = re.split(r'[.!?]+', content)
        
        answer_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 200:
                continue
                
            sentence_lower = sentence.lower()
            
            # Check if sentence contains key terms
            term_count = sum(1 for term in key_terms if term in sentence_lower)
            
            if term_count >= 1:  # At least one key term
                # Clean the sentence
                clean_sentence = self._clean_sentence(sentence)
                if clean_sentence:
                    answer_sentences.append(clean_sentence)
        
        return answer_sentences[:2]  # Top 2 sentences

    def _clean_content_lightly(self, content: str) -> str:
        """Light cleaning that preserves important information."""
        if not content:
            return ""
        
        # Only remove obviously problematic patterns
        content = re.sub(r'\[\d+\]', '', content)  # Citation numbers
        content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
        
        return content.strip()

    def _clean_sentence(self, sentence: str) -> str:
        """Clean individual sentences carefully."""
        if not sentence:
            return ""
        
        # Remove citation marks and normalize
        sentence = re.sub(r'\[\d+\]', '', sentence)
        sentence = re.sub(r'\s+', ' ', sentence)
        sentence = sentence.strip()
        
        # Skip sentences that are clearly navigation/metadata
        skip_patterns = [
            r'^(edit|links|toggle|wikipedia|references|categories)',
            r'^\d+\s+(languages?|references?)',
            r'^(from wikipedia|this article)',
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, sentence, re.IGNORECASE):
                return ""
        
        return sentence

    def _format_sources(self, content_items: List[Dict]) -> str:
        """Format source information clearly."""
        if not content_items:
            return "Sources: Research data collected"
        
        sources = []
        seen_titles = set()
        
        for item in content_items[:5]:  # Limit to 5 sources
            title = item.get("title", "Unknown Source")
            url = item.get("url", "")
            
            if title not in seen_titles:
                if url:
                    sources.append(f"- {title} ({url})")
                else:
                    sources.append(f"- {title}")
                seen_titles.add(title)
        
        if sources:
            return "Sources:\n" + "\n".join(sources)
        else:
            return "Sources: Research data collected"

    def _create_fallback_answer(self, question: str, content_items: List[Dict]) -> str:
        """Create a fallback answer when specific extraction fails."""
        if not content_items:
            return f"Unable to find specific information to answer: {question}"
        
        # Provide available information
        available_info = []
        sources = []
        
        for item in content_items[:2]:  # Use top 2 items
            content = self._clean_content_lightly(item["content"])
            if content:
                preview = content[:300] + "..." if len(content) > 300 else content
                available_info.append(preview)
                sources.append(item)
        
        answer = f"Research conducted for: {question}\n\n"
        answer += "Available information:\n\n"
        
        for i, info in enumerate(available_info, 1):
            answer += f"{i}. {info}\n\n"
        
        answer += self._format_sources(sources)
        
        return answer
