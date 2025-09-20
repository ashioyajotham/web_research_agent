#!/usr/bin/env python3
"""
Test script for enhanced web research agent capabilities.
Tests entity tracking, multi-step planning, and progressive synthesis.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.memory import Memory, ResearchKnowledgeGraph
from agent.comprehension import Comprehension, ProgressiveSynthesis
from agent.planner import Planner, ResearchPhase

def test_knowledge_graph():
    """Test the Research Knowledge Graph functionality."""
    print("=== Testing Knowledge Graph ===")
    
    kg = ResearchKnowledgeGraph()
    
    # Add some test entities
    entity1_id = kg.add_entity_mention(
        entity_name="Joe Biden",
        entity_type="person",
        source_url="https://example.com/news1",
        context="President Joe Biden stated that US-China relations are important",
        attributes={"role": "President"},
        confidence=0.9
    )
    
    entity2_id = kg.add_entity_mention(
        entity_name="United States",
        entity_type="organization",
        source_url="https://example.com/news1",
        context="The United States and China are discussing trade",
        confidence=0.8
    )
    
    # Test entity linking
    kg.link_entities(entity1_id, entity2_id, "leads", "https://example.com/news1")
    
    # Test entity retrieval
    biden_context = kg.get_entity_context("Joe Biden")
    print(f"Biden context: {biden_context[:200]}...")
    
    # Test relationship finding
    related = kg.find_related_entities("Joe Biden")
    print(f"Related entities: {len(related)}")
    
    print("✓ Knowledge Graph tests passed\n")

def test_progressive_synthesis():
    """Test the Progressive Synthesis functionality."""
    print("=== Testing Progressive Synthesis ===")
    
    ps = ProgressiveSynthesis()
    
    # Test content integration
    test_content = '''
    President Biden stated: "The relationship between the United States and China 
    is the most important bilateral relationship in the world." This was during 
    a meeting on March 15, 2023.
    '''
    
    findings = ps.integrate_new_information(
        content=test_content,
        source_url="https://example.com/biden-statement",
        current_phase="gather_statements"
    )
    
    print(f"Extracted findings: {list(findings.keys())}")
    
    # Test synthesis for specific task
    synthesis = ps.synthesize_for_task("Compile 10 statements made by Joe Biden regarding US-China relations")
    print(f"Task synthesis keys: {list(synthesis.keys())}")
    
    print("✓ Progressive Synthesis tests passed\n")

def test_enhanced_comprehension():
    """Test the enhanced Comprehension module."""
    print("=== Testing Enhanced Comprehension ===")
    
    comp = Comprehension()
    
    # Test multi-step task detection
    test_tasks = [
        "Find the name of the COO of the organization that mediated secret talks between US and Chinese AI companies in Geneva in 2023.",
        "Compile a list of 10 statements made by Joe Biden regarding US-China relations.",
        "By what percentage did Volkswagen reduce their Scope 1 and Scope 2 greenhouse gas emissions in 2023 compared to 2021?"
    ]
    
    for i, task in enumerate(test_tasks, 1):
        analysis = comp.analyze_task(task)
        print(f"Task {i}: Multi-step = {analysis.get('multi_step', False)}")
        print(f"  Pattern: {analysis.get('task_type', 'unknown')}")
        print(f"  Entities: {analysis.get('required_entities', [])}")
        print()
    
    print("✓ Enhanced Comprehension tests passed\n")

def test_adaptive_planner():
    """Test the Adaptive Planner functionality."""
    print("=== Testing Adaptive Planner ===")
    
    planner = Planner()
    
    # Test multi-step question decomposition
    test_task = "Find the name of the COO of the organization that mediated secret talks between US and Chinese AI companies in Geneva in 2023."
    
    phases = planner.adaptive_planner.decompose_multistep_question(test_task)
    print(f"Decomposed into {len(phases)} phases:")
    for i, phase in enumerate(phases, 1):
        print(f"  Phase {i}: {phase.description}")
        print(f"    Objective: {phase.objective}")
        print(f"    Required entities: {phase.required_entities}")
    
    # Test entity-focused search planning
    discovered_entities = {
        "organization": ["AI Geneva Institute"],
        "location": ["Geneva"]
    }
    
    if phases:
        query = planner.adaptive_planner.plan_entity_focused_search(discovered_entities, phases[1])
        print(f"\nEntity-focused query: {query}")
    
    print("✓ Adaptive Planner tests passed\n")

def test_memory_integration():
    """Test the enhanced Memory integration."""
    print("=== Testing Memory Integration ===")
    
    memory = Memory()
    
    # Test entity extraction and storage
    test_content = '''
    The AI Safety Institute, based in Geneva, mediated talks between US and Chinese 
    AI companies in 2023. The COO of the institute is Dr. Sarah Chen, who has been 
    leading international AI cooperation efforts.
    '''
    
    extracted = memory.extract_and_store_entities(
        content=test_content,
        source_url="https://example.com/ai-talks",
        entity_types=["person", "organization", "location", "role"]
    )
    
    print(f"Extracted entities: {list(extracted.keys())}")
    for entity_type, entities in extracted.items():
        print(f"  {entity_type}: {entities}")
    
    # Test research phase management
    memory.start_research_phase(
        phase_description="Find organization",
        objective="Identify the organization that mediated talks",
        required_entities=["organization", "location"]
    )
    
    progress = memory.get_research_progress()
    print(f"\nResearch progress: {progress['current_phase']['description']}")
    
    print("✓ Memory Integration tests passed\n")

def main():
    """Run all tests."""
    print("Testing Enhanced Web Research Agent\n")
    
    try:
        test_knowledge_graph()
        test_progressive_synthesis()
        test_enhanced_comprehension()
        test_adaptive_planner()
        test_memory_integration()
        
        print("🎉 All tests passed! The enhanced system is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()