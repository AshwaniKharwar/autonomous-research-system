import logging
import os
from typing import Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger("research_agent")

# Ensure .env is loaded
load_dotenv()


def extract_last_text(result: Any) -> str:
    """Extract string content from LangChain agent invoke result."""
    if isinstance(result, str):
        return result
    if not isinstance(result, dict):
        return str(result)

    messages = result.get("messages")
    if not messages:
        return str(result)

    last_message = messages[-1]
    # Handle message object (BaseMessage) or dict
    content = getattr(last_message, "content", None)
    if content is None and isinstance(last_message, dict):
        content = last_message.get("content", "")

    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content if content is not None else "")


def get_model(role: str = "planner", model_name: str | None = None) -> ChatGoogleGenerativeAI:
    """Factory to obtain ChatGoogleGenerativeAI instance for a given agent role.

    Supports role-specific model overrides with graceful fallback to GEMINI_PLANNER_MODEL.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is missing. "
            "Please ensure it is set in your .env file or environment."
        )

    if model_name is None:
        role_env_keys = {
            "planner": ["GEMINI_PLANNER_MODEL"],
            "architect": ["GEMINI_ARCHITECT_MODEL", "GEMINI_PLANNER_MODEL"],
            "dispatcher": ["GEMINI_DISPATCHER_MODEL", "GEMINI_PLANNER_MODEL"],
            "task": ["GEMINI_TASK_MODEL", "GEMINI_PLANNER_MODEL"],
            "report_writer": ["GEMINI_REPORT_MODEL", "GEMINI_PLANNER_MODEL"],
        }
        candidates = role_env_keys.get(role, ["GEMINI_PLANNER_MODEL"])
        for candidate in candidates:
            val = os.getenv(candidate)
            if val:
                model_name = val
                break

    if not model_name:
        raise ValueError(
            f"No model configured for role '{role}'. "
            "Please set GEMINI_PLANNER_MODEL in your environment."
        )

    return ChatGoogleGenerativeAI(
        api_key=api_key,
        model=model_name,
    )
