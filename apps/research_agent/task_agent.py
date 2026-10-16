import json
import logging
import re
from typing import Any, NamedTuple
from langchain.agents import create_agent
from apps.research_agent.prompts import TaskResearcherAgentPrompt
from apps.research_agent.tools import build_search_tool, fetch_page
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.task_agent")

DEFAULT_SEARCH_BUDGET = 15


class TaskAgentResult(NamedTuple):
    findings: str
    sources: list[dict[str, Any]]

    def get(self, key: str, default: Any = None) -> Any:
        if key == "findings":
            return self.findings
        elif key == "sources":
            return self.sources
        return default


def extract_sources_from_findings(findings_text: str) -> list[dict[str, Any]]:
    """Extract structured source entries from research findings markdown text.

    Parses source citations formatted according to TaskResearcherAgentPrompt, such as:
    [S1] Author/Org. Title. URL. Publication date. Source type.
    as well as markdown links [Title](URL) and raw URL entries.

    Returns a list of dicts with keys: id, url, title, date, snippet.
    """
    if not findings_text:
        return []

    # 1. Try to find the Sources / References section
    sources_section_pattern = re.compile(
        r"(?:^|\n)#{1,4}\s*(?:Sources|References|Bibliography|Citations)\b[^\n]*\n(.*)",
        re.IGNORECASE | re.DOTALL,
    )
    match = sources_section_pattern.search(findings_text)
    if match:
        section_text = match.group(1)
        next_heading = re.search(r"\n#{1,3}\s+[A-Za-z]", section_text)
        if next_heading:
            section_text = section_text[: next_heading.start()]
        candidate_lines = section_text.strip().split("\n")
    else:
        candidate_lines = findings_text.strip().split("\n")

    sources: list[dict[str, Any]] = []
    source_idx = 1
    seen_urls: set[str] = set()

    date_pattern = re.compile(
        r"\b(?:\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|"
        r"(?:\d{1,2}\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|"
        r"(?:19|20)\d{2})\b",
        re.IGNORECASE,
    )

    for line in candidate_lines:
        line = line.strip()
        if not line:
            continue
        cleaned_line = re.sub(r"^(\s*[-*+]\s*|\s*\d+\.\s*)", "", line).strip()

        # Check for citation tag like [S1] or [1]
        tag_match = re.search(r"\[(S\d+|\d+)\]", cleaned_line)
        source_id = None
        if tag_match:
            raw_id = tag_match.group(1)
            source_id = f"S{raw_id}" if raw_id.isdigit() else raw_id

        # In fallback mode (when no Sources heading was matched),
        # only accept lines that have an explicit citation tag [S1] or markdown link or URL
        if not match and not source_id and not ("http://" in cleaned_line or "https://" in cleaned_line):
            continue

        md_match = re.search(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", cleaned_line)
        url = ""
        title = ""
        snippet = ""
        date_str = ""

        if md_match:
            url = md_match.group(2).strip().rstrip(".,;")
            link_title = md_match.group(1).strip()
            before = cleaned_line[: md_match.start()]
            before = re.sub(r"\[S?\d+\][:\s-]*", "", before).strip(" :-.,")
            after = cleaned_line[md_match.end() :].strip(" :-.,")
            title = f"{before} - {link_title}" if before else link_title
            snippet = after
        else:
            url_match = re.search(r"(https?://[^\s\)\]\>]+)", cleaned_line)
            if url_match:
                url = url_match.group(1).strip().rstrip(".,;")
                before = cleaned_line[: url_match.start()]
                before = re.sub(r"\[S?\d+\][:\s-]*", "", before).strip(" :-.,")
                after = cleaned_line[url_match.end() :].strip(" :-.,")
                title = before if before else url
                snippet = after
            else:
                if source_id and match:
                    title = re.sub(r"\[S?\d+\][:\s-]*", "", cleaned_line).strip(" :-.,")
                else:
                    continue

        if not source_id:
            source_id = f"S{source_idx}"

        d_match = date_pattern.search(snippet) or date_pattern.search(cleaned_line)
        if d_match:
            date_str = d_match.group(0)

        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)

        sources.append(
            {
                "id": source_id,
                "url": url,
                "title": title,
                "date": date_str,
                "snippet": snippet,
            }
        )
        source_idx += 1

    return sources


async def run_task_agent(
    task: dict[str, Any],
    dependency_findings: dict[str, str] | None = None,
) -> TaskAgentResult:
    """Run one research task using web research tools and return findings markdown and structured sources."""
    task_id = task.get("task_key") or task.get("id") or "unknown-task"
    task_title = task.get("title", "Untitled Task")
    budget = int(task.get("search_budget") or DEFAULT_SEARCH_BUDGET)

    logger.info(f"Running task agent for {task_id}: '{task_title}' (budget={budget})")
    search_tool = build_search_tool(budget)
    model = get_model("task")

    dep_section = ""
    if dependency_findings:
        dep_texts = []
        for dep_id, finding in dependency_findings.items():
            dep_texts.append(f"### Previous Findings from {dep_id}:\n{finding}")
        dep_section = "Earlier task findings you must build upon:\n" + "\n\n".join(dep_texts)

    prompt = TaskResearcherAgentPrompt.format(
        task=json.dumps(task, indent=2),
        task_id=task_id,
        task_title=task_title,
        search_budget=budget,
        dependency_findings_section=dep_section,
    )

    agent = create_agent(
        model=model,
        tools=[search_tool, fetch_page],
        system_prompt=prompt,
    )

    message = (
        f"Research task {task_id} ('{task_title}') according to its scope, "
        "questions, and budget. Output your complete findings."
    )

    result = await agent.ainvoke(
        {"messages": [("user", message)]},
        config={"recursion_limit": budget * 4 + 25},
    )
    findings_text = extract_last_text(result)
    sources = extract_sources_from_findings(findings_text)
    return TaskAgentResult(findings=findings_text, sources=sources)

