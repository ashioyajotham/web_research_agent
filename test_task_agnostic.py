"""
Task Agnostic System Validation Tests

This script tests the enhanced web research agent across diverse domains
to ensure no brittleness remains after implementing Tongyi techniques.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.planner import Planner
from agent.result_evaluator import ResultEvaluator
from config.config import get_config
import json


def test_task_agnostic_planning():
    """Test planning across diverse task types to ensure no hardcoded brittleness."""
    
    test_cases = [
        {
            "task": "Find 5 statements by Elon Musk about artificial intelligence safety",
            "expected_entities": ["person", "statement", "topic"],
            "domain": "Technology Leadership"
        },
        {
            "task": "What percentage did Netflix reduce their carbon emissions by in 2023?",
            "expected_entities": ["organization", "metric", "date"],
            "domain": "Corporate Sustainability"
        },
        {
            "task": "Find the COO of the organization that mediated the recent Israel-Palestine talks",
            "expected_entities": ["organization", "person", "role"],
            "domain": "International Relations"
        },
        {
            "task": "List companies in Germany that achieved B-Corp certification in 2023",
            "expected_entities": ["organization", "location", "certification"],
            "domain": "Corporate Social Responsibility"
        },
        {
            "task": "Compile 3 quotes from Taylor Swift about mental health awareness",
            "expected_entities": ["person", "statement", "topic"],
            "domain": "Entertainment & Health"
        },
        {
            "task": "What was the revenue increase percentage for Spotify in Q3 2023?",
            "expected_entities": ["organization", "metric", "date"],
            "domain": "Financial Performance"
        },
        {
            "task": "Find the Chief Technology Officer of the company that developed ChatGPT",
            "expected_entities": ["organization", "person", "role"],
            "domain": "AI Technology"
        },
        {
            "task": "Download the IPCC climate dataset and extract temperature anomalies for 2020-2023",
            "expected_entities": ["dataset", "organization", "metric", "date"],
            "domain": "Climate Science"
        }
    ]
    
    planner = Planner()
    results = []
    
    print("=" * 80)
    print("TASK AGNOSTIC SYSTEM VALIDATION TEST")
    print("=" * 80)
    print(f"Testing {len(test_cases)} diverse tasks across multiple domains")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['domain']}")
        print(f"Task: {test_case['task']}")
        print("-" * 60)
        
        # Test planning phase
        try:
            task_analysis = {
                "multi_step": len(test_case['expected_entities']) > 2,
                "required_entities": test_case['expected_entities'],
                "presentation_format": "summary"
            }
            
            plan = planner.create_plan(test_case['task'], task_analysis)
            
            # Analyze plan for brittleness indicators
            brittleness_score = analyze_plan_brittleness(plan, test_case['task'])
            
            # Test entity extraction capability
            sample_content = generate_sample_content_for_domain(test_case['domain'])
            entities = planner.adaptive_planner.extract_entities_from_content(sample_content)
            
            # Test semantic understanding
            subject = planner._extract_statement_subject(test_case['task'])
            topic = planner._extract_statement_topic(test_case['task'])
            
            result = {
                "task": test_case['task'],
                "domain": test_case['domain'],
                "plan_steps": len(plan.steps),
                "brittleness_score": brittleness_score,
                "extracted_entities": list(entities.keys()),
                "semantic_subject": subject,
                "semantic_topic": topic,
                "passed": brittleness_score < 0.3 and len(entities) > 0
            }
            
            print(f"✓ Plan generated: {len(plan.steps)} steps")
            print(f"✓ Brittleness score: {brittleness_score:.2f} (lower is better)")
            print(f"✓ Entity extraction: {list(entities.keys())}")
            print(f"✓ Semantic subject: {subject}")
            print(f"✓ Semantic topic: {topic}")
            print(f"✓ Test {'PASSED' if result['passed'] else 'FAILED'}")
            
        except Exception as e:
            result = {
                "task": test_case['task'],
                "domain": test_case['domain'],
                "error": str(e),
                "passed": False
            }
            print(f"✗ Error: {str(e)}")
            print("✗ Test FAILED")
        
        results.append(result)
        print()
    
    # Generate summary report
    generate_validation_report(results)
    return results


def analyze_plan_brittleness(plan, task_description: str) -> float:
    """Analyze a plan for brittleness indicators."""
    brittleness_score = 0.0
    
    plan_text = str(plan.steps).lower()
    task_lower = task_description.lower()
    
    # Check for hardcoded patterns (should be 0 now)
    hardcoded_patterns = ["biden", "china", "us-china", "joe biden"]
    for pattern in hardcoded_patterns:
        if pattern in plan_text:
            brittleness_score += 0.5  # High penalty for hardcoded patterns
    
    # Check for domain-specific hardcoding
    if "statements" in task_lower and "statements" in plan_text:
        # This is okay - semantic matching
        pass
    elif any(domain_term in plan_text for domain_term in ["biden", "china", "politics"]):
        if not any(domain_term in task_lower for domain_term in ["biden", "china", "politics"]):
            brittleness_score += 0.3  # Penalty for irrelevant domain terms
    
    # Check for adaptive capabilities
    adaptive_indicators = ["entity", "adaptive", "focused", "phase"]
    adaptive_count = sum(1 for indicator in adaptive_indicators if indicator in plan_text)
    
    if adaptive_count == 0:
        brittleness_score += 0.2  # Penalty for non-adaptive planning
    
    # Check for semantic flexibility
    if "{" in plan_text and "}" in plan_text:
        brittleness_score -= 0.1  # Bonus for parameterized plans
    
    return max(0.0, min(1.0, brittleness_score))


def generate_sample_content_for_domain(domain: str) -> str:
    """Generate sample content to test entity extraction across domains."""
    
    domain_samples = {
        "Technology Leadership": """
        Elon Musk, CEO of Tesla and SpaceX, announced in March 2023 that artificial intelligence 
        poses significant risks. The company has invested $2.5 billion in AI safety research.
        """,
        
        "Corporate Sustainability": """
        Netflix Corporation reported a 35% reduction in carbon emissions for 2023, according to 
        their sustainability report published in January 2024. The streaming giant achieved 
        this through renewable energy initiatives.
        """,
        
        "International Relations": """
        The United Nations mediated talks between Israeli and Palestinian representatives in 
        Geneva on December 15, 2023. UN Secretary-General António Guterres led the discussions.
        """,
        
        "Corporate Social Responsibility": """
        Patagonia Inc., based in California, received B-Corp certification in March 2023. 
        The outdoor clothing company met all environmental and social governance criteria.
        """,
        
        "Entertainment & Health": """
        Taylor Swift, the Grammy-winning artist, spoke about mental health awareness during 
        her interview with Rolling Stone in October 2023. She emphasized the importance 
        of seeking professional help.
        """,
        
        "Financial Performance": """
        Spotify Technology S.A. reported Q3 2023 revenue of €3.4 billion, representing a 
        11% increase compared to Q3 2022. Premium subscribers reached 226 million.
        """,
        
        "AI Technology": """
        OpenAI, the company behind ChatGPT, was founded by Sam Altman and others. 
        The organization's Chief Technology Officer is Mira Murati, who oversees 
        AI development initiatives.
        """,
        
        "Climate Science": """
        The IPCC (Intergovernmental Panel on Climate Change) released their 2023 dataset 
        showing temperature anomalies of +1.2°C for 2020, +1.1°C for 2021, +1.15°C for 2022, 
        and +1.4°C for 2023 compared to pre-industrial levels.
        """
    }
    
    return domain_samples.get(domain, "Sample content for entity extraction testing.")


def generate_validation_report(results):
    """Generate a comprehensive validation report."""
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('passed', False))
    pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    avg_brittleness = sum(r.get('brittleness_score', 1.0) for r in results) / total_tests
    
    print("=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed Tests: {passed_tests}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print(f"Average Brittleness Score: {avg_brittleness:.3f} (target: < 0.3)")
    print()
    
    print("DOMAIN COVERAGE:")
    domains = list(set(r['domain'] for r in results))
    for domain in domains:
        domain_results = [r for r in results if r['domain'] == domain]
        domain_pass_rate = (sum(1 for r in domain_results if r.get('passed', False)) / len(domain_results)) * 100
        print(f"  • {domain}: {domain_pass_rate:.0f}% pass rate")
    
    print()
    print("BRITTLENESS ANALYSIS:")
    if avg_brittleness < 0.3:
        print("  ✓ System shows LOW brittleness - task agnostic design successful")
    elif avg_brittleness < 0.5:
        print("  ⚠ System shows MODERATE brittleness - some improvements needed")
    else:
        print("  ✗ System shows HIGH brittleness - significant hardcoding remains")
    
    print()
    print("ENTITY EXTRACTION ANALYSIS:")
    total_entities_extracted = sum(len(r.get('extracted_entities', [])) for r in results)
    avg_entities_per_test = total_entities_extracted / total_tests
    print(f"  • Average entities extracted per test: {avg_entities_per_test:.1f}")
    
    if avg_entities_per_test >= 2.0:
        print("  ✓ Entity extraction is ROBUST across domains")
    elif avg_entities_per_test >= 1.0:
        print("  ⚠ Entity extraction is MODERATE - could be improved")
    else:
        print("  ✗ Entity extraction is WEAK - needs enhancement")
    
    print()
    print("SEMANTIC UNDERSTANDING ANALYSIS:")
    successful_semantic = sum(1 for r in results 
                            if r.get('semantic_subject', '') != 'the specified person' 
                            and r.get('semantic_topic', '') != 'the specified topic')
    semantic_success_rate = (successful_semantic / total_tests) * 100
    print(f"  • Semantic extraction success rate: {semantic_success_rate:.1f}%")
    
    if semantic_success_rate >= 70:
        print("  ✓ Semantic understanding is STRONG")
    elif semantic_success_rate >= 50:
        print("  ⚠ Semantic understanding is MODERATE")
    else:
        print("  ✗ Semantic understanding is WEAK")
    
    print()
    print("OVERALL ASSESSMENT:")
    if pass_rate >= 80 and avg_brittleness < 0.3:
        print("  🎉 SYSTEM TRANSFORMATION SUCCESSFUL!")
        print("     The agent is now truly task-agnostic and robust.")
    elif pass_rate >= 60 and avg_brittleness < 0.5:
        print("  ✓ SYSTEM SIGNIFICANTLY IMPROVED")
        print("     Major brittleness issues resolved, minor improvements remain.")
    else:
        print("  ⚠ SYSTEM NEEDS FURTHER WORK")
        print("     Additional improvements required for full task-agnostic operation.")
    
    # Save detailed results
    with open('validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: validation_results.json")


def test_result_evaluator():
    """Test the result evaluation system."""
    
    print("=" * 80)
    print("RESULT EVALUATOR TESTING")
    print("=" * 80)
    
    evaluator = ResultEvaluator()
    
    # Test different result scenarios
    test_scenarios = [
        {
            "name": "High Quality Result",
            "result": {
                "output": {
                    "extracted_text": "Elon Musk, CEO of Tesla, stated on March 15, 2023 that 'artificial intelligence development should proceed with caution.' This was reported by Reuters and confirmed by multiple sources including the official Tesla blog."
                },
                "status": "success"
            },
            "expected_entities": ["person", "statement", "date"],
            "objective": "Find statements by Elon Musk about AI"
        },
        {
            "name": "Low Quality Result",
            "result": {
                "output": {"extracted_text": "Error 404 - Page not found"},
                "status": "error"
            },
            "expected_entities": ["person", "statement"],
            "objective": "Find statements about technology"
        },
        {
            "name": "Partial Result",
            "result": {
                "output": {
                    "extracted_text": "Tesla is a company. Some information about electric vehicles."
                },
                "status": "success"
            },
            "expected_entities": ["person", "statement", "organization"],
            "objective": "Find CEO statements about company direction"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"Testing: {scenario['name']}")
        print("-" * 40)
        
        evaluation = evaluator.evaluate_step_result(
            scenario['result'],
            scenario['expected_entities'],
            scenario['objective']
        )
        
        print(f"Confidence: {evaluation.confidence:.2f}")
        print(f"Completeness: {evaluation.completeness:.2f}")
        print(f"Relevance: {evaluation.relevance:.2f}")
        print(f"Overall Score: {evaluation.overall_score:.2f}")
        print(f"Should Replan: {evaluation.should_replan}")
        print(f"Missing Entities: {evaluation.missing_entities}")
        print(f"Suggested Actions: {evaluation.suggested_actions}")
        print()
    
    print("Result evaluator testing completed!")


if __name__ == "__main__":
    print("Starting comprehensive task-agnostic system validation...")
    print()
    
    # Test planning system
    planning_results = test_task_agnostic_planning()
    
    print()
    
    # Test result evaluation
    test_result_evaluator()
    
    print()
    print("🎯 All validation tests completed!")
    print("Check validation_results.json for detailed analysis.")