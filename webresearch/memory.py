"""
Conversation memory for multi-turn research sessions.
Maintains Q&A context across queries within a single CLI session.
"""

from typing import List, Tuple


class ConversationMemory:
    """
    Stores previous Q&A pairs and injects them as context into new queries.

    Keeps up to `max_pairs` most-recent exchanges so the LLM can build on
    prior research without exceeding reasonable prompt sizes.
    """

    def __init__(self, max_pairs: int = 5):
        self.max_pairs = max_pairs
        self._pairs: List[Tuple[str, str]] = []  # (query, answer)

    def add(self, query: str, answer: str) -> None:
        """Record a completed Q&A pair."""
        self._pairs.append((query, answer))
        if len(self._pairs) > self.max_pairs:
            self._pairs.pop(0)

    def clear(self) -> None:
        """Reset the session memory."""
        self._pairs = []

    def __len__(self) -> int:
        return len(self._pairs)

    def get_context(self) -> str:
        """Return a formatted string of previous Q&A pairs for LLM context."""
        if not self._pairs:
            return ""

        lines = ["PREVIOUS RESEARCH CONTEXT (from this session):"]
        for i, (q, a) in enumerate(self._pairs, 1):
            a_preview = a[:600] + "…" if len(a) > 600 else a
            lines.append(f"\n[Q{i}] {q}")
            lines.append(f"[A{i}] {a_preview}")
        return "\n".join(lines)

    def build_task_with_memory(self, query: str) -> str:
        """Prepend session context to a new query so the agent can reference prior work."""
        context = self.get_context()
        if not context:
            return query
        return f"{context}\n\nCURRENT QUESTION:\n{query}"
