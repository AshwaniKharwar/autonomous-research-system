import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from apps.research_agent.prompts import (
    LeadEditorAgentPrompt,
    ReportWriterAgentPrompt,
    SectionWriterAgentPrompt,
)
from apps.research_agent.report_writer import (
    _draft_section,
    _group_tasks_by_section,
    _lead_editor_synthesis,
    _order_sections,
    _single_pass_synthesis,
    report_writer,
)


def test_prompt_formatting():
    """Verify all prompts format properly without syntax or KeyError issues."""
    p1 = SectionWriterAgentPrompt.format(
        query="What is quantum computing?",
        section_title="Hardware Architectures",
        tasks_summary="[]",
        section_findings="### Findings: Superconducting qubits...",
    )
    assert "Hardware Architectures" in p1
    assert "Superconducting qubits" in p1

    p2 = LeadEditorAgentPrompt.format(
        query="What is quantum computing?",
        plan_content="# Research Plan",
        tasks_summary="[]",
        drafted_sections="## Hardware Architectures\nNarrative here",
    )
    assert "Hardware Architectures" in p2
    assert "Consolidated Sources" in p2

    p3 = ReportWriterAgentPrompt.format(
        query="What is quantum computing?",
        plan_content="# Research Plan",
        tasks_summary="[]",
        all_findings="Findings...",
    )
    assert "Report Compiler Agent" in p3


def test_group_tasks_by_section():
    """Verify task grouping by feeds_report_section and angle."""
    tasks = [
        {
            "task_key": "task-01",
            "title": "Battery Chemistry",
            "feeds_report_section": "Architecture & Chemistry",
        },
        {
            "task_key": "task-02",
            "title": "Solid Electrolytes",
            "feeds_report_section": "Architecture & Chemistry",
        },
        {
            "task_key": "task-03",
            "title": "Energy Density Benchmarks",
            "angle": "Performance & Safety",
        },
        {
            "task_key": "task-04",
            "title": "General Notes",
        },
    ]
    findings = {
        "task-01": "Lithium metal anodes offer higher capacity.",
        "task-02": "Sulfide electrolytes have high conductivity.",
        "task-03": "Demonstrated 450 Wh/kg in pouch cells.",
        "task-04": "Regulatory overview notes.",
    }

    sections = _group_tasks_by_section(tasks, findings)

    assert "Architecture & Chemistry" in sections
    assert "Performance & Safety" in sections
    assert "General Findings" in sections

    arch_sec = sections["Architecture & Chemistry"]
    assert len(arch_sec["tasks"]) == 2
    assert len(arch_sec["findings"]) == 2
    # Verify finding isolation
    f_texts = [f[2] for f in arch_sec["findings"]]
    assert "Lithium metal anodes offer higher capacity." in f_texts
    assert "Sulfide electrolytes have high conductivity." in f_texts
    assert "Demonstrated 450 Wh/kg in pouch cells." not in f_texts

    perf_sec = sections["Performance & Safety"]
    assert len(perf_sec["tasks"]) == 1
    assert len(perf_sec["findings"]) == 1
    assert perf_sec["findings"][0][2] == "Demonstrated 450 Wh/kg in pouch cells."

    gen_sec = sections["General Findings"]
    assert len(gen_sec["tasks"]) == 1
    assert gen_sec["findings"][0][2] == "Regulatory overview notes."


def test_order_sections():
    """Verify outline-based section ordering matching the plan outline."""
    plan_content = """
    # Research Plan
    ## Report Outline
    1. Executive Summary
    2. Architecture & Chemistry
    3. Performance & Safety
    4. Manufacturing Challenges
    5. Commercial Readiness
    """
    section_names = [
        "Manufacturing Challenges",
        "Architecture & Chemistry",
        "Commercial Readiness",
        "Custom Unlisted Section",
        "Performance & Safety",
    ]

    ordered = _order_sections(section_names, plan_content)
    assert ordered == [
        "Architecture & Chemistry",
        "Performance & Safety",
        "Manufacturing Challenges",
        "Commercial Readiness",
        "Custom Unlisted Section",
    ]


@pytest.mark.asyncio
async def test_hierarchical_two_stage_compiler_execution():
    """Verify the 2-stage hierarchical report compilation with parallel section drafting and lead editor synthesis."""
    query = "Solid-state battery commercial readiness"
    plan_content = """
    # Research Plan
    ## Report Outline
    1. Executive Summary
    2. Technology Architecture
    3. Commercial Landscape
    """
    tasks = [
        {
            "task_key": "task-01",
            "title": "Electrolyte Architecture",
            "feeds_report_section": "Technology Architecture",
        },
        {
            "task_key": "task-02",
            "title": "Market Landscape",
            "feeds_report_section": "Commercial Landscape",
        },
    ]
    findings = {
        "task-01": "Sulfide and oxide solid electrolytes analyzed [S1].",
        "task-02": "Toyota and QuantumScape targeting 2027-2028 [S2].",
    }

    mock_model = MagicMock()

    # Track invocations for Stage 1 and Stage 2
    section_draft_invocations = []

    async def mock_draft_section(section_name, query, section_tasks, section_findings, model):
        section_draft_invocations.append({
            "section_name": section_name,
            "tasks": section_tasks,
            "findings": section_findings,
        })
        # Simulate slight delay to test concurrency
        await asyncio.sleep(0.01)
        return section_name, f"## {section_name}\nDrafted narrative for {section_name}."

    async def mock_lead_editor(query, plan_content, tasks, drafted_sections, model):
        assert "## Technology Architecture" in drafted_sections
        assert "## Commercial Landscape" in drafted_sections
        return (
            "# Master Research Report: Solid-state battery commercial readiness\n\n"
            "## Executive Summary\nSSBs represent the next frontier...\n\n"
            "## Key Takeaways\n- Commercial scale expected by 2027-2028.\n\n"
            f"{drafted_sections}\n\n"
            "## Consolidated Sources\n[1] Toyota Tech Review 2024\n[2] QuantumScape SEC 2025"
        )


    with patch("apps.research_agent.report_writer.get_model", return_value=mock_model), \
         patch("apps.research_agent.report_writer._draft_section", side_effect=mock_draft_section), \
         patch("apps.research_agent.report_writer._lead_editor_synthesis", side_effect=mock_lead_editor):

        report = await report_writer(
            query=query,
            plan_content=plan_content,
            tasks=tasks,
            findings=findings,
        )

    # Verify Stage 1 was called for each section concurrently
    assert len(section_draft_invocations) == 2
    sec_names = {inv["section_name"] for inv in section_draft_invocations}
    assert sec_names == {"Technology Architecture", "Commercial Landscape"}

    # Verify findings isolation in Stage 1
    tech_inv = next(i for i in section_draft_invocations if i["section_name"] == "Technology Architecture")
    assert len(tech_inv["findings"]) == 1
    assert "Sulfide and oxide" in tech_inv["findings"][0][2]

    comm_inv = next(i for i in section_draft_invocations if i["section_name"] == "Commercial Landscape")
    assert len(comm_inv["findings"]) == 1
    assert "Toyota and QuantumScape" in comm_inv["findings"][0][2]

    # Verify final report content
    assert "# Master Research Report" in report
    assert "## Executive Summary" in report
    assert "## Key Takeaways" in report
    assert "## Technology Architecture" in report
    assert "## Commercial Landscape" in report
    assert "## Consolidated Sources" in report


@pytest.mark.asyncio
async def test_fallback_when_tasks_have_no_feeds_report_section():
    """Verify graceful fallback to single-pass synthesis when tasks lack section metadata."""
    query = "Simple Query"
    plan_content = "# Plan"
    tasks = [
        {"task_key": "t1", "title": "Task 1"},
        {"task_key": "t2", "title": "Task 2"},
    ]
    findings = {"t1": "Findings 1", "t2": "Findings 2"}

    mock_single_pass = AsyncMock(return_value="# Single Pass Report")

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._single_pass_synthesis", mock_single_pass):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Single Pass Report"
    assert mock_single_pass.call_count == 1


@pytest.mark.asyncio
async def test_fallback_when_all_tasks_group_into_single_section():
    """Verify graceful fallback to single-pass synthesis when all tasks belong to only one section."""
    query = "Single Section Query"
    plan_content = "# Plan"
    tasks = [
        {"task_key": "t1", "title": "Task 1", "feeds_report_section": "Sole Section"},
        {"task_key": "t2", "title": "Task 2", "feeds_report_section": "Sole Section"},
    ]
    findings = {"t1": "Findings 1", "t2": "Findings 2"}

    mock_single_pass = AsyncMock(return_value="# Single Section Fallback Report")

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._single_pass_synthesis", mock_single_pass):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Single Section Fallback Report"
    assert mock_single_pass.call_count == 1


@pytest.mark.asyncio
async def test_fallback_when_findings_empty():
    """Verify graceful fallback when findings dictionary is empty."""
    query = "Empty Findings Query"
    plan_content = "# Plan"
    tasks = [
        {"task_key": "t1", "title": "Task 1", "feeds_report_section": "Sec 1"},
        {"task_key": "t2", "title": "Task 2", "feeds_report_section": "Sec 2"},
    ]
    findings = {}

    mock_single_pass = AsyncMock(return_value="# Empty Findings Report")

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._single_pass_synthesis", mock_single_pass):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Empty Findings Report"
    assert mock_single_pass.call_count == 1


@pytest.mark.asyncio
async def test_fallback_when_only_one_section_has_findings():
    """Verify graceful fallback when tasks span multiple sections but only one has findings."""
    query = "Partial Findings Query"
    plan_content = "# Plan"
    tasks = [
        {"task_key": "t1", "title": "Task 1", "feeds_report_section": "Sec 1"},
        {"task_key": "t2", "title": "Task 2", "feeds_report_section": "Sec 2"},
    ]
    # Only t1 has findings
    findings = {"t1": "Findings for t1"}

    mock_single_pass = AsyncMock(return_value="# Partial Findings Fallback")

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._single_pass_synthesis", mock_single_pass):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Partial Findings Fallback"
    assert mock_single_pass.call_count == 1


@pytest.mark.asyncio
async def test_section_draft_error_resilience():
    """Verify that if one section drafting call fails, raw findings fallback is used and compilation succeeds."""
    query = "Resilience Query"
    plan_content = "# Plan\n## Report Outline\n1. Sec 1\n2. Sec 2"
    tasks = [
        {"task_key": "t1", "title": "Task 1", "feeds_report_section": "Sec 1"},
        {"task_key": "t2", "title": "Task 2", "feeds_report_section": "Sec 2"},
    ]
    findings = {"t1": "Findings 1", "t2": "Findings 2"}

    # Mock create_agent so that t1 succeeds but t2 raises
    mock_agent_success = MagicMock()
    mock_agent_success.ainvoke = AsyncMock(return_value={"messages": [MagicMock(content="## Sec 1\nSuccess narrative")]})

    mock_agent_fail = MagicMock()
    mock_agent_fail.ainvoke = AsyncMock(side_effect=RuntimeError("LLM API error on Sec 2"))

    def mock_create_agent(model, tools, system_prompt):
        if "Sec 2" in system_prompt:
            return mock_agent_fail
        return mock_agent_success

    mock_lead_editor = AsyncMock(return_value="# Final Resilient Report")

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer.create_agent", side_effect=mock_create_agent), \
         patch("apps.research_agent.report_writer._lead_editor_synthesis", mock_lead_editor):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Final Resilient Report"
    assert mock_lead_editor.call_count == 1

    # Check the drafted_sections passed to lead editor
    call_args = mock_lead_editor.call_args[1]
    drafted_sections = call_args["drafted_sections"]
    # Sec 1 had successful narrative
    assert "Success narrative" in drafted_sections
    # Sec 2 had fallback narrative with raw findings
    assert "Findings 2" in drafted_sections


@pytest.mark.asyncio
async def test_bounded_concurrency_in_stage1_section_drafting(monkeypatch):
    """Verify that Stage 1 section drafting respects MAX_CONCURRENT_REPORT_SECTIONS concurrency limit."""
    monkeypatch.setenv("MAX_CONCURRENT_REPORT_SECTIONS", "2")

    query = "Concurrency test"
    plan_content = "# Plan"
    tasks = [
        {"task_key": f"t{i}", "title": f"Task {i}", "feeds_report_section": f"Section {i}"}
        for i in range(5)
    ]
    findings = {f"t{i}": f"Finding {i}" for i in range(5)}

    current_concurrency = 0
    max_observed_concurrency = 0

    async def mock_draft(section_name, query, section_tasks, section_findings, model):
        nonlocal current_concurrency, max_observed_concurrency
        current_concurrency += 1
        if current_concurrency > max_observed_concurrency:
            max_observed_concurrency = current_concurrency
        await asyncio.sleep(0.02)
        current_concurrency -= 1
        return section_name, f"## {section_name}\nDrafted"

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._draft_section", side_effect=mock_draft), \
         patch("apps.research_agent.report_writer._lead_editor_synthesis", return_value="# Final Report"):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Final Report"
    assert max_observed_concurrency <= 2
    assert max_observed_concurrency > 1


@pytest.mark.asyncio
async def test_section_draft_retry_on_transient_error_success(monkeypatch):
    """Verify _draft_section retries transient errors (e.g., 429) and returns synthesized narrative on recovery."""
    monkeypatch.setenv("REPORT_SECTION_MAX_RETRIES", "2")
    monkeypatch.setenv("REPORT_SECTION_RETRY_SLEEP", "0.001")

    attempts = 0
    mock_agent_fail = MagicMock()
    mock_agent_fail.ainvoke = AsyncMock(side_effect=Exception("429 ResourceExhausted: Rate limit reached"))

    mock_agent_success = MagicMock()
    mock_agent_success.ainvoke = AsyncMock(return_value={"messages": [MagicMock(content="## Architecture\nSynthesized Content")]})

    def mock_create_agent(model, tools, system_prompt):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return mock_agent_fail
        return mock_agent_success

    with patch("apps.research_agent.report_writer.create_agent", side_effect=mock_create_agent):
        sec_name, narrative = await _draft_section(
            section_name="Architecture",
            query="test",
            section_tasks=[{"task_key": "t1", "title": "T1"}],
            section_findings=[("t1", "T1", "Raw findings content")],
            model=MagicMock(),
        )

    assert attempts == 2
    assert "Synthesized Content" in narrative


@pytest.mark.asyncio
async def test_section_draft_non_transient_error_no_retry(monkeypatch):
    """Verify _draft_section does NOT retry non-transient errors and falls back immediately."""
    monkeypatch.setenv("REPORT_SECTION_MAX_RETRIES", "2")
    monkeypatch.setenv("REPORT_SECTION_RETRY_SLEEP", "0.001")

    attempts = 0
    mock_agent_fail = MagicMock()
    mock_agent_fail.ainvoke = AsyncMock(side_effect=ValueError("Invalid argument format"))

    def mock_create_agent(model, tools, system_prompt):
        nonlocal attempts
        attempts += 1
        return mock_agent_fail

    with patch("apps.research_agent.report_writer.create_agent", side_effect=mock_create_agent):
        sec_name, narrative = await _draft_section(
            section_name="Architecture",
            query="test",
            section_tasks=[{"task_key": "t1", "title": "T1"}],
            section_findings=[("t1", "T1", "Raw findings content")],
            model=MagicMock(),
        )

    assert attempts == 1
    assert "Raw findings content" in narrative


@pytest.mark.asyncio
async def test_section_draft_transient_exhaustion_fallback(monkeypatch):
    """Verify _draft_section falls back to raw findings when retries are exhausted."""
    monkeypatch.setenv("REPORT_SECTION_MAX_RETRIES", "2")
    monkeypatch.setenv("REPORT_SECTION_RETRY_SLEEP", "0.001")

    attempts = 0
    mock_agent_fail = MagicMock()
    mock_agent_fail.ainvoke = AsyncMock(side_effect=TimeoutError("Request timed out"))

    def mock_create_agent(model, tools, system_prompt):
        nonlocal attempts
        attempts += 1
        return mock_agent_fail

    with patch("apps.research_agent.report_writer.create_agent", side_effect=mock_create_agent):
        sec_name, narrative = await _draft_section(
            section_name="Architecture",
            query="test",
            section_tasks=[{"task_key": "t1", "title": "T1"}],
            section_findings=[("t1", "T1", "Raw findings content")],
            model=MagicMock(),
        )

    assert attempts == 3
    assert "Raw findings content" in narrative


@pytest.mark.asyncio
async def test_stage2_fallback_to_single_pass_synthesis():
    """Verify that if Stage 2 lead editor synthesis fails, it gracefully falls back to _single_pass_synthesis."""
    query = "Stage 2 Failure Query"
    plan_content = "# Plan"
    tasks = [
        {"task_key": "t1", "title": "T1", "feeds_report_section": "Sec 1"},
        {"task_key": "t2", "title": "T2", "feeds_report_section": "Sec 2"},
    ]
    findings = {"t1": "Findings 1", "t2": "Findings 2"}

    mock_draft = AsyncMock(side_effect=lambda section_name, **kwargs: (section_name, f"## {section_name}\nDraft"))
    mock_lead_editor = AsyncMock(side_effect=RuntimeError("Context window limit exceeded"))
    mock_single_pass = AsyncMock(return_value="# Single-Pass Fallback Report")

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._draft_section", mock_draft), \
         patch("apps.research_agent.report_writer._lead_editor_synthesis", mock_lead_editor), \
         patch("apps.research_agent.report_writer._single_pass_synthesis", mock_single_pass):

        report = await report_writer(query, plan_content, tasks, findings)

    assert report == "# Single-Pass Fallback Report"
    assert mock_lead_editor.call_count == 1
    assert mock_single_pass.call_count == 1


@pytest.mark.asyncio
async def test_stage2_multi_tier_fallback_to_assembled_drafts():
    """Verify that if BOTH Stage 2 lead editor and single-pass fallback fail, it falls back to direct assembly."""
    query = "Total Failure Query"
    plan_content = "# Plan"
    tasks = [
        {"task_key": "t1", "title": "T1", "feeds_report_section": "Sec 1"},
        {"task_key": "t2", "title": "T2", "feeds_report_section": "Sec 2"},
    ]
    findings = {"t1": "Findings 1", "t2": "Findings 2"}

    mock_draft = AsyncMock(side_effect=lambda section_name, **kwargs: (section_name, f"## {section_name}\nDraft narrative"))
    mock_lead_editor = AsyncMock(side_effect=RuntimeError("Lead editor failure"))
    mock_single_pass = AsyncMock(side_effect=RuntimeError("Single pass failure"))

    with patch("apps.research_agent.report_writer.get_model"), \
         patch("apps.research_agent.report_writer._draft_section", mock_draft), \
         patch("apps.research_agent.report_writer._lead_editor_synthesis", mock_lead_editor), \
         patch("apps.research_agent.report_writer._single_pass_synthesis", mock_single_pass):

        report = await report_writer(query, plan_content, tasks, findings)

    assert "# Research Report: Total Failure Query" in report
    assert "## Executive Summary" in report
    assert "## Sec 1\nDraft narrative" in report
    assert "## Sec 2\nDraft narrative" in report

