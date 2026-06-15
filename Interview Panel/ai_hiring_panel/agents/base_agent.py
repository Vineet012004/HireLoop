"""Base class shared by all interview agents."""
from abc import ABC, abstractmethod
from llm.groq_client import chat_completion
from config import get_settings

settings = get_settings()


class BaseInterviewAgent(ABC):
    """
    Abstract interview agent.  Subclasses define their system prompt
    and any domain-specific logic; this class handles the conversation loop.
    """

    agent_type: str = "base"

    def __init__(self, candidate_info: dict, resume_text: str):
        """
        Args:
            candidate_info: Structured dict produced by resume.analyzer.
            resume_text: Raw resume text for deeper context.
        """
        self.candidate_info = candidate_info
        self.resume_text = resume_text
        self.conversation: list[dict] = []  # accumulates {"role", "content"} pairs
        self._initialize_system_prompt()

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Return the system prompt that defines this agent's persona."""

    def _initialize_system_prompt(self):
        system_prompt = self._build_system_prompt()
        self.conversation = [{"role": "system", "content": system_prompt}]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_opening_message(self) -> str:
        """Generate the first message the agent sends to open the interview."""
        self.conversation.append(
            {
                "role": "user",
                "content": "Please start the interview with a warm greeting and your first question.",
            }
        )
        reply = chat_completion(self.conversation, temperature=0.7)
        self.conversation.append({"role": "assistant", "content": reply})
        return reply

    def respond(self, candidate_answer: str) -> str:
        """
        Feed the candidate's answer and return the agent's next question/response.

        Args:
            candidate_answer: The text the candidate typed.

        Returns:
            The agent's follow-up message.
        """
        self.conversation.append({"role": "user", "content": candidate_answer})
        reply = chat_completion(self.conversation, temperature=0.7)
        self.conversation.append({"role": "assistant", "content": reply})
        return reply

    def close_interview(self) -> str:
        """Ask the agent to wrap up the interview gracefully."""
        self.conversation.append(
            {
                "role": "user",
                "content": (
                    "Please wrap up the interview now. Thank the candidate, "
                    "let them know next steps, and say goodbye."
                ),
            }
        )
        reply = chat_completion(self.conversation, temperature=0.6)
        self.conversation.append({"role": "assistant", "content": reply})
        return reply

    def get_transcript(self) -> list[dict]:
        """Return all conversation turns (excluding system prompt)."""
        return [m for m in self.conversation if m["role"] != "system"]
