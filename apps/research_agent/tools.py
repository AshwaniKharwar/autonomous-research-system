from langchain_core.tools import tool
from tavily import AsyncTavilyClient
from dotenv import load_dotenv
import os

BASE_DIR = "/Users/ashwanikharwar/workspace/research_system/apps/research_agent/research"

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

def _validate_path(path: str) -> str:
    """Validate that the path is within BASE_DIR"""
    # Convert to absolute path if it's not already
    if not os.path.isabs(path):
        abs_path = os.path.join(BASE_DIR, path)
    else:
        abs_path = path

    # Normalize the path (resolve .. and .)
    normalized_path = os.path.normpath(abs_path)

    # Ensure the path is within BASE_DIR with proper directory boundary check
    if not _path_within_base_dir(normalized_path):
        raise ValueError(f"Access denied: {path} is outside the allowed research directory")

    return normalized_path


def _path_within_base_dir(path: str) -> bool:
    """Check if the given path is within BASE_DIR."""
    if not path.startswith(os.path.normpath(BASE_DIR)):
        return False
    if path == os.path.normpath(BASE_DIR):
        return True
    if len(path) > len(os.path.normpath(BASE_DIR)):
        return path[len(os.path.normpath(BASE_DIR))] == os.sep
    return False

@tool
async def list_files(directory: str) -> list[str]:
    """List all files in a directory within the research folder"""
    try:
        print("listing files...")
        validated_path = _validate_path(directory)
        return os.listdir(validated_path)
    except Exception as e:
        return f"Error: {str(e)}"

@tool
async def read_file(file_path: str) -> str:
    """Read a file within the research folder"""
    try:
        print("Reading file....")
        validated_path = _validate_path(file_path)
        with open(validated_path, "r") as file:
            return file.read()
    except Exception as e:
        return f"Error: {str(e)}"

@tool
async def write_file(file_path: str, content: str) -> str:
    """Write to a file within the research folder"""
    try:
        print("Writitng file...")
        validated_path = _validate_path(file_path)
        with open(validated_path, "w") as file:
            file.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
async def create_directory(directory_path: str) -> str:
    """Create a directory within the research folder"""
    try:
        print("Creating directory...")
        validated_path = _validate_path(directory_path)
        os.makedirs(validated_path, exist_ok=True)
        return f"Successfully created directory: {directory_path}"
    except Exception as e:
        return f"Error: {str(e)}"


async def _tavily_search(query: str, max_results: int) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set"
    try:
        client = AsyncTavilyClient(api_key=api_key)
        response = await client.search(query, max_results=max_results)
        results = response.get("results", [])
        if not results:
            return "No results found."

        print("Formating web search...")

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result.get('title', 'Untitled')}\n"
                f"   URL: {result.get('url', '')}\n"
                f"   {result.get('content', '')}"
            )
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error: {str(e)}"


@tool
async def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for up-to-date information using Tavily"""
    print("Searching the web....")
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
        print("Searching the web....")
        counter["count"] += 1
        if counter["count"] > budget:
            return (
                f"Search budget of {budget} queries is exhausted. "
                "Stop searching and write your findings from the evidence you already have."
            )
        return await _tavily_search(query, max_results)

    return budgeted_search_web


@tool
async def fetch_page(url: str) -> str:
    """Fetch and read the full text of one web page (use after search_web)."""
    print("Fetching page....")
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set"
    try:
        client = AsyncTavilyClient(api_key=api_key)
        response = await client.extract(urls=[url])
        results = response.get("results", [])
        if not results:
            failed = response.get("failed_results", [])
            return f"No content found. Failed: {failed}"

        print("Formating page content...")

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
        return f"Error: {str(e)}"




