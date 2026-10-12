import logging
import os
from pathlib import Path
from typing import Union
from dotenv import load_dotenv
from langchain_core.tools import tool
from tavily import AsyncTavilyClient

logger = logging.getLogger("research_agent.tools")

BASE_DIR = str(Path(__file__).resolve().parent / "research")

load_dotenv()

_async_tavily_client: AsyncTavilyClient | None = None


def _get_tavily_client() -> AsyncTavilyClient:
    global _async_tavily_client
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set")
    if _async_tavily_client is None:
        _async_tavily_client = AsyncTavilyClient(api_key=api_key)
    return _async_tavily_client


def _validate_path(path: str) -> Path:
    """Validate that the path is within BASE_DIR and return resolved Path object."""
    base = Path(BASE_DIR).resolve()
    p = Path(path)
    if not p.is_absolute():
        resolved_path = (base / p).resolve()
    else:
        resolved_path = p.resolve()

    if not resolved_path.is_relative_to(base):
        raise ValueError(f"Access denied: {path} is outside the allowed research directory ({BASE_DIR})")

    return resolved_path


def _path_within_base_dir(path: str) -> bool:
    """Check if the given path is within BASE_DIR."""
    try:
        base = Path(BASE_DIR).resolve()
        p = Path(path).resolve()
        return p.is_relative_to(base)
    except Exception:
        return False


@tool
async def list_files(directory: str) -> Union[list[str], str]:
    """List all files in a directory within the research folder"""
    try:
        logger.info(f"Listing files in directory: {directory}")
        validated_path = _validate_path(directory)
        return os.listdir(validated_path)
    except Exception as e:
        logger.error(f"Failed to list files in {directory}: {e}")
        return f"Error: {str(e)}"


@tool
async def read_file(file_path: str) -> str:
    """Read a file within the research folder"""
    try:
        logger.info(f"Reading file: {file_path}")
        validated_path = _validate_path(file_path)
        with open(validated_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool
async def write_file(file_path: str, content: str) -> str:
    """Write to a file within the research folder"""
    try:
        logger.info(f"Writing file: {file_path}")
        validated_path = _validate_path(file_path)
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validated_path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool
async def create_directory(directory_path: str) -> str:
    """Create a directory within the research folder"""
    try:
        logger.info(f"Creating directory: {directory_path}")
        validated_path = _validate_path(directory_path)
        os.makedirs(validated_path, exist_ok=True)
        return f"Successfully created directory: {directory_path}"
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}")
        return f"Error: {str(e)}"


async def _tavily_search(query: str, max_results: int) -> str:
    try:
        client = _get_tavily_client()
        response = await client.search(query, max_results=max_results)
        results = response.get("results", [])
        if not results:
            return "No results found."

        logger.info("Formatting web search results...")

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result.get('title', 'Untitled')}\n"
                f"   URL: {result.get('url', '')}\n"
                f"   {result.get('content', '')}"
            )
        return "\n\n".join(formatted)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Error: {str(e)}"


@tool
async def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for up-to-date information using Tavily"""
    logger.info(f"Searching the web for: {query}")
    return await _tavily_search(query, max_results)


def build_search_tool(budget: int):
    """Build a search_web tool that refuses to run after `budget` calls.

    Each task run gets its own counter, so concurrent tasks never share or
    exhaust each other's budget.
    """
    counter = {"count": 0}

    @tool("search_web")
    async def budgeted_search_web(query: str, max_results: int = 5) -> str:
        """Search the web for up-to-date information using Tavily"""
        logger.info(f"Budgeted web search ({counter['count'] + 1}/{budget}): {query}")
        if counter["count"] >= budget:
            return (
                f"Search budget of {budget} queries is exhausted. "
                "Stop searching and write your findings from the evidence you already have."
            )
        counter["count"] += 1
        return await _tavily_search(query, max_results)

    return budgeted_search_web


@tool
async def fetch_page(url: str) -> str:
    """Fetch and read the full text of one web page (use after search_web)."""
    logger.info(f"Fetching page: {url}")
    try:
        client = _get_tavily_client()
        response = await client.extract(urls=[url])
        results = response.get("results", [])
        if not results:
            failed = response.get("failed_results", [])
            return f"No content found. Failed: {failed}"

        logger.info("Formatting page content...")

        formatted = []
        for result in results:
            formatted.append(
                f"{result.get('title', 'Untitled')}\n"
                f"URL: {result.get('url', url)}\n"
                f"{result.get('raw_content', '')}"
            )
        failed = response.get("failed_results", [])
        if failed:
            formatted.append(f"(Some pages failed to fetch: {failed})")
        return "\n\n".join(formatted)
    except Exception as e:
        logger.error(f"Failed to fetch page {url}: {e}")
        return f"Error: {str(e)}"
