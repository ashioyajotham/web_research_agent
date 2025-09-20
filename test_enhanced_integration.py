#!/usr/bin/env python3
"""
Test script for the enhanced capabilities integration from your friend's improvements.
"""

from agent.memory import ResearchKnowledgeGraph
from agent.comprehension import Comprehension, TaskComponent, TaskAnalysis

def test_enhanced_memory():
    """Test enhanced memory capabilities."""
    print('=== Testing Enhanced Memory Capabilities ===')
    kg = ResearchKnowledgeGraph()

    # Add test entities
    org_id = kg.add_entity('AI Safety Institute', 'organization', 'https://example.com/news', 
                          'The AI Safety Institute mediated talks in Geneva', attributes={'location': 'Geneva'})

    person_id = kg.add_entity('Dr. Sarah Chen', 'person', 'https://example.com/news',
                             'Dr. Sarah Chen serves as COO of the institute', attributes={'role': 'COO'})

    kg.link_entities(person_id, org_id, 'works_at', 'https://example.com/news')

    # Test new strategic methods
    print('Testing get_entity_by_role...')
    coo = kg.get_entity_by_role('COO')
    print(f'Found COO: {coo.name if coo else "None"}')

    print('Testing get_organization_from_event...')
    org = kg.get_organization_from_event(['talks', 'Geneva'])
    print(f'Found organization from event: {org.name if org else "None"}')

    print('Testing get_connected_entities...')
    connected = kg.get_connected_entities('Dr. Sarah Chen')
    print(f'Connected entities: {[e.name for e in connected]}')
    
    return True

def test_enhanced_comprehension():
    """Test enhanced comprehension capabilities."""
    print('\n=== Testing Enhanced Comprehension Capabilities ===')
    comp = Comprehension()

    # Test TaskComponent creation
    task = 'Find the COO of the organization that mediated talks between US and Chinese AI companies in Geneva in 2023'
    analysis = comp.analyze_task(task)

    print(f'Task analysis type: {analysis.get("task_type")}')
    print(f'Multi-step: {analysis.get("multi_step")}')
    print(f'Components: {len(analysis.get("components", []))} found')
    
    if 'information_flow' in analysis:
        print('Information flow mapping:')
        for desc, flow in analysis['information_flow'].items():
            print(f'  - {desc}: {flow}')
    
    if 'components' in analysis:
        print('Task components:')
        for i, component in enumerate(analysis['components'], 1):
            print(f'  {i}. {component.description}')
            print(f'     - Required entities: {component.required_entities}')
            print(f'     - Search strategy: {component.search_strategy}')
            if component.depends_on:
                print(f'     - Depends on: {component.depends_on}')
    
    return True

def main():
    """Run integration tests."""
    try:
        test_enhanced_memory()
        test_enhanced_comprehension()
        print('\n✅ Enhanced capabilities integration test completed successfully!')
        return True
    except Exception as e:
        print(f'\n❌ Integration test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)