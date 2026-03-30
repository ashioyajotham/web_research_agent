"""
Think tool — gives the agent an explicit reasoning slot without external side effects.

The agent uses this to plan its approach, verify an entity found in search results
actually matches the task description, or decide whether to change direction.
No API calls, no scraping — just structured reasoning before acting.
"""

from .base import Tool


class ThinkTool(Tool):
    """A no-op tool that records a reasoning step without taking any external action."""

    @property
    def name(self) -> str:
        return "think"

    @property
    def description(self) -> str:
        return """Use this tool to reason through a problem before taking an action.
No external calls are made — it is a private reasoning step.

Parameters:
- thought (str, required): Your reasoning. Can include plans, evaluations,
  or verification of whether evidence found so far actually answers the question.

Returns:
Confirms the thought was recorded.

Use this tool when:
- Planning which searches to run before starting, especially for multi-part questions
- Checking whether an organization or person found in search results genuinely matches
  the description in the task (not just a superficially related entity)
- Deciding whether current evidence is sufficient or whether more searching is needed
- Changing research direction after a dead end
"""

    def execute(self, thought: str) -> str:
        # Return a neutral confirmation — the value is in the reasoning, not the result
        return "Reasoning recorded. Proceed with your next action."
