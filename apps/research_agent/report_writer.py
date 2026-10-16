import asyncio
import json
import logging
import os
from typing import Any
from langchain.agents import create_agent
from apps.research_agent.prompts import (
    LeadEditorAgentPrompt,
    ReportWriterAgentPrompt,
    SectionWriterAgentPrompt,
)
from apps.research_agent.utils import extract_last_text, get_model, is_transient_error

logger = logging.getLogger("research_agent.report_writer")



def _group_tasks_by_section(
    tasks: list[dict[str, Any]],
    findings: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Group tasks and their corresponding findings by target report section."""
    sections: dict[str, dict[str, Any]] = {}
    unassigned_tasks: list[dict[str, Any]] = []
    unassigned_findings: list[tuple[str, str, str]] = []

    for t in tasks:
        task_id = str(t.get("task_key") or t.get("id") or "").strip()
        sec_name = str(t.get("feeds_report_section") or t.get("angle") or "").strip()
        f_content = findings.get(task_id) or findings.get(str(t.get("task_key", ""))) or findings.get(str(t.get("id", "")))
        task_title = t.get("title") or task_id

        if not sec_name:
            unassigned_tasks.append(t)
            if f_content:
                unassigned_findings.append((task_id, task_title, f_content))
            continue

        if sec_name not in sections:
            sections[sec_name] = {"tasks": [], "findings": []}
        sections[sec_name]["tasks"].append(t)
        if f_content:
            sections[sec_name]["findings"].append((task_id, task_title, f_content))

    # If multiple named sections exist and there are unassigned tasks with findings,
    # group them under a "General Findings" section to preserve the evidence.
    if unassigned_findings and len(sections) >= 1:
        sections["General Findings"] = {
            "tasks": unassigned_tasks,
            "findings": unassigned_findings,
        }

    return sections


def _order_sections(
    section_names: list[str],
    plan_content: str,
) -> list[str]:
    """Order section names according to the outline in plan_content, if available."""
    if not plan_content:
        return section_names

    plan_lower = plan_content.lower()

    def get_sort_key(sec: str) -> tuple[int, int]:
        pos = plan_lower.find(sec.lower())
        if pos != -1:
            return (0, pos)
        # Not found in plan: sort after matched sections, preserving original order
        return (1, 0)

    return sorted(section_names, key=get_sort_key)


async def _single_pass_synthesis(
    query: str,
    plan_content: str,
    tasks: list[dict[str, Any]],
    findings: dict[str, str],
    model: Any | None = None,
) -> str:
    """Fallback single-pass monolithic report synthesis."""
    logger.info("Executing single-pass report synthesis (fallback)...")
    if model is None:
        model = get_model("report_writer")

    tasks_summary = json.dumps(
        [
            {
                "task_key": t.get("task_key") or t.get("id"),
                "title": t.get("title"),
                "feeds_report_section": t.get("feeds_report_section") or t.get("angle"),
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


async def _draft_section(
    section_name: str,
    query: str,
    section_tasks: list[dict[str, Any]],
    section_findings: list[tuple[str, str, str]],
    model: Any,
) -> tuple[str, str]:
    """Draft narrative for a single report section based on its tasks and findings."""
    logger.info(f"Stage 1: Drafting section narrative for '{section_name}' with {len(section_findings)} task findings...")
    tasks_summary = json.dumps(
        [
            {
                "task_key": t.get("task_key") or t.get("id"),
                "title": t.get("title"),
                "questions": t.get("questions", []),
                "scope": t.get("scope", ""),
            }
            for t in section_tasks
        ],
        indent=2,
    )

    formatted_findings = "\n\n---\n\n".join(
        [
            f"### Task Findings: {task_id} ({task_title})\n{content}"
            for task_id, task_title, content in section_findings
        ]
    )

    prompt = SectionWriterAgentPrompt.format(
        query=query,
        section_title=section_name,
        tasks_summary=tasks_summary,
        section_findings=formatted_findings,
    )

    max_retries = int(os.getenv("REPORT_SECTION_MAX_RETRIES", "2"))
    retry_sleep_base = float(os.getenv("REPORT_SECTION_RETRY_SLEEP", "0.5"))

    for attempt in range(max_retries + 1):
        try:
            agent = create_agent(
                model=model,
                tools=[],
                system_prompt=prompt,
            )

            result = await agent.ainvoke({
                "messages": [
                    ("user", f"Draft the comprehensive section narrative for '{section_name}' based on the provided findings.")
                ]
            })

            narrative = extract_last_text(result)
            return section_name, narrative
        except Exception as e:
            if attempt < max_retries and is_transient_error(e):
                logger.warning(
                    f"Drafting section '{section_name}' attempt {attempt + 1} failed with transient error: {e}. Retrying..."
                )
                await asyncio.sleep(retry_sleep_base * (attempt + 1))
                continue
            logger.error(f"Failed to draft section '{section_name}': {e}", exc_info=True)
            break

    # Graceful fallback: assemble raw findings for this section
    fallback_narrative = (
        f"## {section_name}\n\n"
        + "\n\n".join(
            [f"### Findings for {task_id} ({task_title}):\n{content}" for task_id, task_title, content in section_findings]
        )
    )
    return section_name, fallback_narrative



async def _lead_editor_synthesis(
    query: str,
    plan_content: str,
    tasks: list[dict[str, Any]],
    drafted_sections: str,
    model: Any,
) -> str:
    """Lead Editor synthesis pass to compile executive summary, assemble sections, and unify citations."""
    logger.info("Stage 2: Executing Lead Editor synthesis pass...")

    tasks_summary = json.dumps(
        [
            {
                "task_key": t.get("task_key") or t.get("id"),
                "title": t.get("title"),
                "feeds_report_section": t.get("feeds_report_section") or t.get("angle"),
            }
            for t in tasks
        ],
        indent=2,
    )

    prompt = LeadEditorAgentPrompt.format(
        query=query,
        plan_content=plan_content,
        tasks_summary=tasks_summary,
        drafted_sections=drafted_sections,
    )

    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=prompt,
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", f"Synthesize and edit the drafted sections into a master final report for the query: {query}")
        ]
    })

    return extract_last_text(result)


async def report_writer(
    query: str,
    plan_content: str,
    tasks: list[dict[str, Any]],
    findings: dict[str, str],
) -> str:
    """Compile the final synthesized research report from all findings using a two-stage hierarchical compiler."""
    logger.info("Starting report compilation...")
    model = get_model("report_writer")

    # Group tasks by their target report section
    sections = _group_tasks_by_section(tasks, findings)
    sections_with_findings = {
        sec: data for sec, data in sections.items() if data["findings"]
    }

    # Graceful fallback: If all tasks have no feeds_report_section or group into a single section,
    # or if there is at most 1 section with findings, fall back cleanly to single-pass synthesis.
    if len(sections_with_findings) <= 1:
        logger.info(
            f"Falling back to single-pass report synthesis (sections with findings: {len(sections_with_findings)})..."
        )
        return await _single_pass_synthesis(
            query=query,
            plan_content=plan_content,
            tasks=tasks,
            findings=findings,
            model=model,
        )

    # Order sections according to the outline in plan_content
    ordered_section_names = _order_sections(list(sections_with_findings.keys()), plan_content)

    # Stage 1: Section drafting in parallel with concurrency semaphore
    concurrency_limit = max(1, int(os.getenv("MAX_CONCURRENT_REPORT_SECTIONS", "3")))
    semaphore = asyncio.Semaphore(concurrency_limit)
    logger.info(
        f"Stage 1: Concurrently drafting {len(ordered_section_names)} section narratives "
        f"(max concurrency: {concurrency_limit})..."
    )

    async def _draft_section_with_semaphore(sec_name: str) -> tuple[str, str]:
        async with semaphore:
            return await _draft_section(
                section_name=sec_name,
                query=query,
                section_tasks=sections_with_findings[sec_name]["tasks"],
                section_findings=sections_with_findings[sec_name]["findings"],
                model=model,
            )

    draft_tasks = [
        _draft_section_with_semaphore(sec_name)
        for sec_name in ordered_section_names
    ]
    drafted_results = await asyncio.gather(*draft_tasks)
    drafted_map = dict(drafted_results)

    # Assemble drafted body sections in outline order
    assembled_drafts = "\n\n---\n\n".join(
        [drafted_map[sec_name] for sec_name in ordered_section_names if sec_name in drafted_map]
    )

    # Stage 2: Lead Editor / Executive Synthesis pass
    logger.info("Stage 2: Running Lead Editor executive synthesis pass...")
    try:
        final_report = await _lead_editor_synthesis(
            query=query,
            plan_content=plan_content,
            tasks=tasks,
            drafted_sections=assembled_drafts,
            model=model,
        )
    except Exception as e:
        logger.error(
            f"Stage 2 lead editor synthesis failed: {e}. Falling back to single-pass compilation.",
            exc_info=True,
        )
        try:
            final_report = await _single_pass_synthesis(
                query=query,
                plan_content=plan_content,
                tasks=tasks,
                findings=findings,
                model=model,
            )
        except Exception as single_pass_err:
            logger.error(
                f"Single-pass fallback synthesis failed: {single_pass_err}. Assembling drafted sections directly.",
                exc_info=True,
            )
            final_report = (
                f"# Research Report: {query}\n\n"
                f"## Executive Summary\n"
                f"Report synthesized from {len(tasks)} tasks across {len(ordered_section_names)} sections.\n\n"
                f"{assembled_drafts}"
            )

    logger.info("Hierarchical report compilation completed successfully.")
    return final_report

