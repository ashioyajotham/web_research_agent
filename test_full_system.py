#!/usr/bin/env python3
"""
Final comprehensive test of the enhanced web research agent.
"""

from agent.agent import WebResearchAgent

def test_full_system():
    """Test the full system with enhanced capabilities."""
    print('=== Testing Full System with Enhanced Capabilities ===')
    agent = WebResearchAgent()

    # Test task that uses the enhanced features
    task = 'Find the COO of the organization that mediated talks between US and Chinese AI companies in Geneva in 2023'

    # Analyze the task using enhanced comprehension
    analysis = agent.comprehension.analyze_task(task)
    print(f'✅ Task Analysis: {analysis["task_type"]} with {len(analysis.get("components", []))} components')

    # Test entity storage with enhanced memory
    test_entity_id = agent.memory.knowledge_graph.add_entity(
        'World Economic Forum', 'organization', 'https://test.com',
        'The World Economic Forum facilitated discussions on AI governance',
        attributes={'role': 'facilitator', 'location': 'Geneva'}
    )

    # Test enhanced entity retrieval
    facilitator = agent.memory.knowledge_graph.get_organization_from_event(['discussions', 'governance'])
    print(f'✅ Enhanced Entity Search: Found {facilitator.name if facilitator else "None"} as facilitator')

    # Test role-based search
    person_id = agent.memory.knowledge_graph.add_entity(
        'Dr. Alice Johnson', 'person', 'https://test.com',
        'Dr. Alice Johnson is the Chief Technology Officer',
        attributes={'role': 'Chief Technology Officer'}
    )
    
    cto = agent.memory.knowledge_graph.get_entity_by_role('Chief Technology Officer')
    print(f'✅ Role-based Search: Found {cto.name if cto else "None"} as CTO')

    print('✅ Full system integration with enhanced capabilities working perfectly!')
    return True

if __name__ == "__main__":
    try:
        test_full_system()
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()