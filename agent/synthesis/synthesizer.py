from typing import List, Dict
from ..comprehension.task_analyzer import TaskIntent, TaskRequirements

class ResultSynthesizer:
    def synthesize(self, results: List[Dict], requirements: TaskRequirements) -> Dict:
        """Synthesize results based on task requirements"""
        if not results:
            return self._create_empty_response(requirements)
            
        synthesizers = {
            TaskIntent.COMPILE: self._synthesize_compilation,
            TaskIntent.FIND: self._synthesize_fact,
            TaskIntent.ANALYZE: self._synthesize_analysis,
            TaskIntent.CALCULATE: self._synthesize_calculation,
            TaskIntent.EXTRACT: self._synthesize_extraction,
            TaskIntent.VERIFY: self._synthesize_verification
        }
        
        synthesizer = synthesizers.get(requirements.intent, self._synthesize_default)
        return synthesizer(results, requirements)

    def _synthesize_compilation(self, results: List[Dict], requirements: TaskRequirements) -> Dict:
        """Synthesize list-type results with proper formatting"""
        compiled_items = []
        seen = set()
        limit = requirements.count if requirements.count else len(results)
        
        for idx, result in enumerate(results):
            if idx >= limit:
                break
                
            content = result.get('snippet', '').strip()
            content_key = content.lower() if content else ''
            
            if content and content_key not in seen:
                seen.add(content_key)
                compiled_items.append({
                    'content': content,
                    'metadata': {
                        'source': result.get('link'),
                        'date': result.get('date')
                    }
                })
        
        return {
            'type': 'compilation',
            'items': compiled_items,
            'total_found': len(compiled_items)
        }

    def _synthesize_fact(self, results: List[Dict], requirements: TaskRequirements) -> Dict:
        """Synthesize fact-finding results with verification"""
        if not results:
            return {'type': 'fact', 'answer': None}
            
        best_result = results[0]
        supporting = []
        
        # Safer list iteration instead of slicing
        remaining_results = results[1:]
        support_count = 0
        for result in remaining_results:
            if support_count >= 2:  # Limit to 2 supporting sources
                break
            if result.get('link'):
                supporting.append(result.get('link'))
                support_count += 1
            
        return {
            'type': 'fact',
            'answer': best_result.get('snippet', '').strip(),
            'confidence': 'high' if supporting and self._verify_fact(results) else 'medium',
            'source': best_result.get('link'),
            'supporting_sources': supporting
        }

    def _verify_fact(self, results: List[Dict]) -> bool:
        """Verify fact consistency across multiple sources"""
        if len(results) < 2:
            return False
            
        # Use explicit indexing instead of slicing
        main_content = results[0].get('snippet', '').lower()
        verified = False
        
        # Check up to 2 additional sources
        for i in range(1, min(3, len(results))):
            comparison_content = results[i].get('snippet', '').lower()
            if self._content_similarity(main_content, comparison_content):
                verified = True
                break
                
        return verified

    def _content_similarity(self, text1: str, text2: str) -> bool:
        """Basic content similarity check"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        common_words = words1.intersection(words2)
        return len(common_words) / max(len(words1), len(words2)) > 0.3

    def _apply_format_requirements(self, item: Dict, requirements: TaskRequirements) -> Dict:
        """Apply formatting requirements to items"""
        formatted = {}
        if 'separate_items' in requirements.format_requirements:
            formatted['format'] = 'separate'
        if 'include_dates' in requirements.format_requirements:
            formatted['date_required'] = True
        return formatted

    def _create_empty_response(self, requirements: TaskRequirements) -> Dict:
        return {
            'type': requirements.intent.value,
            'content': None,
            'error': 'No results found'
        }
