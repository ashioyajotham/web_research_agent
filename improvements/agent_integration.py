# In your tool registry setup (tools/__init__.py or wherever you register tools)

from tools.improved_presentation_tool import ImprovedPresentationTool

# Replace the old presentation tool registration
def setup_tools():
    """Setup all tools for the agent."""
    tools = {}
    
    # Keep your existing tools
    tools['search'] = SearchTool()
    tools['browser'] = BrowserTool()
    tools['code_generator'] = CodeGeneratorTool()
    
    # Replace with improved presentation tool
    tools['present'] = ImprovedPresentationTool()
    tools['presentation'] = ImprovedPresentationTool()  # For backward compatibility
    
    return tools

# In your main agent execution loop, add debugging
def execute_research_task(self, task_description: str) -> Dict[str, Any]:
    """Execute research task with improved debugging."""
    logger.info(f"Starting research task: {task_description}")
    
    # Your existing task analysis
    analysis = self.comprehension.analyze_task(task_description)
    logger.info(f"Task analysis: {analysis}")
    
    # Your existing planning
    plan = self.planner.create_plan(analysis)
    logger.info(f"Created plan with {len(plan.steps)} steps")
    
    # Execute with detailed logging
    results = []
    for i, step in enumerate(plan.steps):
        logger.info(f"Executing step {i+1}: {step.description}")
        result = self.execute_step(step)
        logger.info(f"Step {i+1} result: {result.get('status', 'unknown')}")
        results.append(result)
    
    # The improved presentation tool will now provide better results
    return {"analysis": analysis, "plan": plan, "results": results}
