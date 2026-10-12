import json
import logging
from typing import Any
from langchain.agents import create_agent
from apps.research_agent.prompts import ReportWriterAgentPrompt
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.report_writer")


async def report_writer(
    query: str,
    plan_content: str,
    tasks: list[dict[str, Any]],
    findings: dict[str, str],
) -> str:
    """Compile the final synthesized research report from all findings."""
    logger.info("Compiling final research report...")
    model = get_model("report_writer")

    tasks_summary = json.dumps(
        [
            {
                "task_key": t.get("task_key"),
                "title": t.get("title"),
                "feeds_report_section": t.get("feeds_report_section"),
            }
            for t in tasks
        ],
        indent=2,
    )

    formatted_findings = "\n\n---\n\n".join(
        [f"## Findings for {task_id}:\n{content}" for task_id, content in findings.items()]
    )

    prompt = ReportWriterAgentPrompt.format(
        query=query,
        plan_content=plan_content,
        tasks_summary=tasks_summary,
        all_findings=formatted_findings,
    )

    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=prompt,
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", f"Synthesize all research findings into a comprehensive final report for the query: {query}")
        ]
    })
    return extract_last_text(result)
