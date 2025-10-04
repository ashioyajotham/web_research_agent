"""
ReAct Agent Implementation.

This implements the ReAct (Reasoning and Acting) paradigm from the paper:
"ReAct: Synergizing Reasoning and Acting in Language Models"

The agent follows a loop:
1. Thought: Reason about what to do next
2. Action: Execute a tool with specific parameters
3. Observation: Receive the result
4. Repeat until the task is complete
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from llm import LLMInterface
from tools import ToolManager

logger = logging.getLogger(__name__)


@dataclass
class Step:
    """Represents a single step in the ReAct loop."""

    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class ReActAgent:
    """
    ReAct agent that reasons about and executes tasks using available tools.

    The agent follows the ReAct paradigm:
    - Thought: Reasoning about the current state and what to do next
    - Action: Executing a tool to gather information or perform an operation
    - Observation: Processing the result of the action
    """

    def __init__(
        self,
        llm: LLMInterface,
        tool_manager: ToolManager,
        max_iterations: int = 15,
        max_tool_output_length: int = 5000,
    ):
        """
        Initialize the ReAct agent.

        Args:
            llm: The language model interface
            tool_manager: Manager for available tools
            max_iterations: Maximum number of reasoning iterations
            max_tool_output_length: Maximum length of tool output to include in context
        """
        self.llm = llm
        self.tool_manager = tool_manager
        self.max_iterations = max_iterations
        self.max_tool_output_length = max_tool_output_length
        self.steps: List[Step] = []

    def run(self, task: str) -> str:
        """
        Run the agent on a given task.

        Args:
            task: The task description

        Returns:
            The final answer
        """
        logger.info(f"Starting task: {task[:100]}...")
        self.steps = []

        try:
            for iteration in range(self.max_iterations):
                logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

                # Generate the next thought and action
                prompt = self._build_prompt(task)
                response = self.llm.generate(prompt)

                # Parse the response
                thought, action, action_input, final_answer = self._parse_response(
                    response
                )

                # Create a step for this iteration
                step = Step(thought=thought)

                # Check if we have a final answer
                if final_answer:
                    logger.info("Agent produced final answer")
                    self.steps.append(step)
                    return final_answer

                # Execute the action if present
                if action and action_input is not None:
                    step.action = action
                    step.action_input = action_input

                    # Execute the tool
                    observation = self._execute_action(action, action_input)
                    step.observation = observation

                    self.steps.append(step)
                    logger.info(
                        f"Action: {action}, Observation length: {len(observation)}"
                    )
                else:
                    # No valid action, prompt the agent to continue
                    step.observation = "No valid action found. Please provide a thought and then an action."
                    self.steps.append(step)

            # Max iterations reached
            logger.warning("Max iterations reached without final answer")
            return self._generate_best_effort_answer(task)

        except Exception as e:
            logger.error(f"Error during agent execution: {str(e)}")
            return f"Error: The agent encountered an error: {str(e)}"

    def _build_prompt(self, task: str) -> str:
        """
        Build the prompt for the LLM including task, tools, and history.

        Args:
            task: The task description

        Returns:
            The complete prompt
        """
        prompt_parts = []

        # System instructions
        prompt_parts.append("""You are a research agent that can use tools to complete tasks. You follow the ReAct (Reasoning and Acting) paradigm.

For each step, you should:
1. Think about what you need to do next (Thought)
2. Decide on an action to take using one of the available tools (Action)
3. Specify the parameters for the action (Action Input)
4. Observe the result (Observation - this will be provided to you)

When you have enough information to answer the task, provide your final answer.

FORMAT:
You must use this exact format:

Thought: [your reasoning about what to do next]
Action: [the tool name to use]
Action Input: [the parameters as a JSON object]

OR, when you have the final answer:

Thought: [your reasoning about why you have enough information]
Final Answer: [your complete answer to the task]

IMPORTANT RULES:
- Always start with "Thought:" to explain your reasoning
- Use "Action:" only when you want to use a tool
- Use "Action Input:" with valid JSON for parameters
- Use "Final Answer:" only when you can fully answer the task
- Be thorough and verify information from multiple sources when needed
- For tasks requiring lists or compilations, gather comprehensive information before concluding
- Always provide sources and citations in your final answer when applicable
""")

        # Add tool descriptions
        prompt_parts.append("\n" + self.tool_manager.get_tool_descriptions())

        # Add the task
        prompt_parts.append(f"\n\nTASK:\n{task}")

        # Add history of previous steps
        if self.steps:
            prompt_parts.append("\n\nPREVIOUS STEPS:")
            for i, step in enumerate(self.steps, 1):
                prompt_parts.append(f"\nStep {i}:")
                prompt_parts.append(f"Thought: {step.thought}")

                if step.action:
                    prompt_parts.append(f"Action: {step.action}")
                    prompt_parts.append(
                        f"Action Input: {self._format_action_input(step.action_input)}"
                    )

                if step.observation:
                    # Truncate observation if too long
                    obs = step.observation
                    if len(obs) > self.max_tool_output_length:
                        obs = (
                            obs[: self.max_tool_output_length]
                            + f"\n... [truncated from {len(step.observation)} chars]"
                        )
                    prompt_parts.append(f"Observation: {obs}")

        # Prompt for next step
        prompt_parts.append("\n\nWhat is your next step?")

        return "\n".join(prompt_parts)

    def _parse_response(
        self, response: str
    ) -> tuple[str, Optional[str], Optional[Dict], Optional[str]]:
        """
        Parse the LLM response to extract thought, action, and parameters.

        Args:
            response: The LLM response text

        Returns:
            Tuple of (thought, action, action_input, final_answer)
        """
        thought = ""
        action = None
        action_input = None
        final_answer = None

        # Extract Thought
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\n(?:Action|Final Answer):|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Check for Final Answer
        final_answer_match = re.search(
            r"Final Answer:\s*(.+)", response, re.DOTALL | re.IGNORECASE
        )
        if final_answer_match:
            final_answer = final_answer_match.group(1).strip()
            return thought, None, None, final_answer

        # Extract Action
        action_match = re.search(r"Action:\s*(\w+)", response, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()

        # Extract Action Input
        action_input_match = re.search(
            r"Action Input:\s*(\{.+?\}|\{.+)", response, re.DOTALL | re.IGNORECASE
        )
        if action_input_match:
            action_input_str = action_input_match.group(1).strip()
            # Try to parse as JSON
            try:
                import json

                # Handle incomplete JSON by finding the matching brace
                brace_count = 0
                end_idx = 0
                for i, char in enumerate(action_input_str):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

                if end_idx > 0:
                    action_input_str = action_input_str[:end_idx]

                action_input = json.loads(action_input_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse action input as JSON: {e}")
                # Try to extract key-value pairs manually
                action_input = self._parse_action_input_fallback(action_input_str)

        return thought, action, action_input, final_answer

    def _parse_action_input_fallback(self, action_input_str: str) -> Dict[str, Any]:
        """
        Fallback parser for action input when JSON parsing fails.

        Args:
            action_input_str: The action input string

        Returns:
            Dictionary of parameters
        """
        params = {}

        # Try to extract key: value or key=value patterns
        patterns = [
            r'"(\w+)":\s*"([^"]+)"',  # "key": "value"
            r"'(\w+)':\s*'([^']+)'",  # 'key': 'value'
            r'(\w+):\s*"([^"]+)"',  # key: "value"
            r"(\w+)=([^,}\s]+)",  # key=value
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, action_input_str)
            for match in matches:
                key, value = match.groups()
                params[key] = value

        return params

    def _format_action_input(self, action_input: Optional[Dict]) -> str:
        """
        Format action input for display.

        Args:
            action_input: The action input dictionary

        Returns:
            Formatted string
        """
        if not action_input:
            return "{}"

        import json

        try:
            return json.dumps(action_input, indent=2)
        except:
            return str(action_input)

    def _execute_action(self, action: str, action_input: Dict[str, Any]) -> str:
        """
        Execute a tool action.

        Args:
            action: The tool name
            action_input: The tool parameters

        Returns:
            The observation from executing the tool
        """
        try:
            result = self.tool_manager.execute_tool(action, **action_input)
            return result
        except Exception as e:
            logger.error(f"Error executing action {action}: {str(e)}")
            return f"Error executing action: {str(e)}"

    def _generate_best_effort_answer(self, task: str) -> str:
        """
        Generate a best-effort answer when max iterations is reached.

        Args:
            task: The original task

        Returns:
            A summary of what was found
        """
        prompt = f"""The agent reached the maximum number of iterations while working on this task:

TASK:
{task}

Based on the information gathered in these steps, provide the best possible answer:

"""
        # Add step summaries
        for i, step in enumerate(self.steps, 1):
            prompt += f"\nStep {i}:\n"
            prompt += f"Thought: {step.thought}\n"
            if step.observation:
                obs = step.observation[:1000]  # Truncate
                prompt += f"Observation: {obs}...\n"

        prompt += "\n\nProvide a final answer based on the information gathered:"

        try:
            response = self.llm.generate(prompt)
            return f"[Note: Max iterations reached. Best effort answer:]\n\n{response}"
        except Exception as e:
            return f"Unable to complete the task within {self.max_iterations} iterations. Last thought: {self.steps[-1].thought if self.steps else 'N/A'}"

    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """
        Get the execution trace of all steps.

        Returns:
            List of step dictionaries
        """
        trace = []
        for i, step in enumerate(self.steps, 1):
            step_dict = {
                "step": i,
                "thought": step.thought,
            }
            if step.action:
                step_dict["action"] = step.action
                step_dict["action_input"] = step.action_input
            if step.observation:
                step_dict["observation"] = (
                    step.observation[:500] + "..."
                    if len(step.observation) > 500
                    else step.observation
                )
            trace.append(step_dict)
        return trace
