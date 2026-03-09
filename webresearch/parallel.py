"""
Parallel research agent that decomposes queries and fans out to sub-agents.
Inspired by gpt-researcher's parallel investigation architecture.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple

from .agent import ReActAgent
from .llm import LLMInterface
from .tools import ToolManager

logger = logging.getLogger(__name__)


class ParallelResearchAgent:
    """
    Research agent that fans out a query into N parallel sub-investigations,
    then synthesizes all results into a comprehensive answer.

    Flow:
      1. Decompose  — LLM breaks the query into max_sub_queries focused sub-questions
      2. Research   — Each sub-question is run by a lightweight mini-ReActAgent
                      concurrently via ThreadPoolExecutor (I/O-bound Gemini calls
                      release the GIL, so true concurrency is achieved)
      3. Synthesize — LLM merges all sub-results into one coherent answer
    """

    def __init__(
        self,
        llm: LLMInterface,
        tool_manager: ToolManager,
        max_sub_queries: int = 4,
        sub_iterations: int = 5,
        max_workers: int = 3,
    ):
        self.llm = llm
        self.tool_manager = tool_manager
        self.max_sub_queries = max_sub_queries
        self.sub_iterations = sub_iterations
        self.max_workers = max_workers
        self._sub_results: List[Tuple[str, str]] = []

    def run(
        self,
        task: str,
        sub_status_callback: Optional[Callable] = None,
    ) -> str:
        """
        Run parallel research on the given task.

        Args:
            task: The research question.
            sub_status_callback: Optional callable(idx, state, question=None).
                state is one of: 'pending' | 'running' | 'done' | 'error'.

        Returns:
            Synthesized final answer.
        """
        logger.info(f"ParallelResearchAgent starting: {task[:80]}")

        # ── 1. Decompose ──────────────────────────────────────────────────────
        sub_questions = self._decompose(task)
        logger.info(f"Decomposed into {len(sub_questions)} sub-questions")

        if sub_status_callback:
            for i, q in enumerate(sub_questions):
                sub_status_callback(i, "pending", q)

        # ── 2. Research in parallel ───────────────────────────────────────────
        results: Dict[int, Tuple[str, str]] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_to_idx = {
                pool.submit(self._research_sub_question, q, i, sub_status_callback): i
                for i, q in enumerate(sub_questions)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                q = sub_questions[idx]
                try:
                    answer = future.result()
                    results[idx] = (q, answer)
                    if sub_status_callback:
                        sub_status_callback(idx, "done")
                except Exception as e:
                    logger.error(f"Sub-query {idx} failed: {e}")
                    results[idx] = (q, f"Research failed: {e}")
                    if sub_status_callback:
                        sub_status_callback(idx, "error")

        # ── 3. Synthesize ─────────────────────────────────────────────────────
        ordered = [results[i] for i in range(len(sub_questions))]
        self._sub_results = ordered
        logger.info("Synthesizing sub-results")
        return self._synthesize(task, ordered)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _decompose(self, task: str) -> List[str]:
        """Ask the LLM to break the task into N focused sub-questions."""
        prompt = (
            f"You are a research planner. Break the following question into "
            f"{self.max_sub_queries} focused sub-questions that together would "
            f"answer the original question comprehensively.\n\n"
            f"RESEARCH QUESTION: {task}\n\n"
            f"Output ONLY a numbered list, one sub-question per line. No preamble.\n"
            f"SUB-QUESTIONS:"
        )
        try:
            response = self.llm.generate(prompt)
            sub_questions = []
            for line in response.strip().splitlines():
                m = re.match(r"^\d+[.)]\s*(.+)", line.strip())
                if m:
                    sub_questions.append(m.group(1).strip())
            if len(sub_questions) >= 2:
                return sub_questions[: self.max_sub_queries]
        except Exception as e:
            logger.warning(f"Decomposition failed: {e}, using original query")
        return [task]

    def _research_sub_question(
        self,
        question: str,
        idx: int,
        sub_status_callback: Optional[Callable] = None,
    ) -> str:
        """Run a mini ReAct loop for a single sub-question."""
        if sub_status_callback:
            sub_status_callback(idx, "running")

        mini_agent = ReActAgent(
            llm=self.llm,
            tool_manager=self.tool_manager,
            max_iterations=self.sub_iterations,
        )
        return mini_agent.run(question)

    def _synthesize(self, task: str, sub_results: List[Tuple[str, str]]) -> str:
        """Combine all sub-results into a comprehensive final answer."""
        parts = [
            f"You are a research synthesizer. Below are results from "
            f"{len(sub_results)} parallel investigations into different "
            f"aspects of a research question.\n",
            f"ORIGINAL QUESTION: {task}\n",
            "SUB-INVESTIGATION RESULTS:",
        ]
        for i, (q, a) in enumerate(sub_results, 1):
            preview = a[:1500] + ("…" if len(a) > 1500 else "")
            parts.append(f"\n--- Sub-query {i}: {q} ---\n{preview}")

        parts.append(
            f"\n\nUsing all the above research, write a comprehensive, "
            f"well-structured answer to: {task}\n"
            f"Integrate findings from all sub-queries. Note any conflicting "
            f"information. Cite sources where mentioned above."
        )

        try:
            return self.llm.generate("\n".join(parts))
        except Exception as e:
            # Fallback: concatenate sub-results
            fallback = [f"[Synthesis failed: {e}]\n\nResearch findings:\n"]
            for i, (q, a) in enumerate(sub_results, 1):
                fallback.append(f"\n## {i}. {q}\n{a[:800]}")
            return "\n".join(fallback)

    def get_execution_trace(self) -> List[Dict]:
        return [
            {
                "sub_query": i + 1,
                "question": q,
                "answer_preview": a[:200],
            }
            for i, (q, a) in enumerate(self._sub_results)
        ]
