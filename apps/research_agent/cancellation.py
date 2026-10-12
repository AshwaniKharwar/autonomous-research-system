import asyncio
import logging
from uuid import UUID

logger = logging.getLogger("research_agent.cancellation")


class CancellationToken:
    """Manages cancellation signaling for an in-flight research session."""

    def __init__(self, session_id: UUID) -> None:
        self.session_id = session_id
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._event.is_set()


# In-memory registry mapping session_id to its CancellationToken
_tokens: dict[UUID, CancellationToken] = {}
_lock = asyncio.Lock()


def register_token(session_id: UUID) -> CancellationToken:
    """Register or retrieve an existing CancellationToken for a session."""
    if session_id not in _tokens:
        _tokens[session_id] = CancellationToken(session_id)
        logger.debug(f"Registered cancellation token for session {session_id}")
    return _tokens[session_id]


def get_token(session_id: UUID) -> CancellationToken | None:
    """Retrieve CancellationToken for a session if registered."""
    return _tokens.get(session_id)


def is_cancelled(session_id: UUID) -> bool:
    """Check if cancellation has been signaled for a session."""
    token = _tokens.get(session_id)
    return token.is_cancelled if token is not None else False


def cancel_session(session_id: UUID) -> bool:
    """Signal cancellation for a session. Returns True if a token was signaled."""
    token = register_token(session_id)
    token.cancel()
    logger.info(f"Signaled cancellation for session {session_id}")
    return True


def clear_token(session_id: UUID) -> None:
    """Remove a session's token from memory once execution terminates."""
    if session_id in _tokens:
        del _tokens[session_id]
        logger.debug(f"Cleared cancellation token for session {session_id}")
