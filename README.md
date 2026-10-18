# Multi-Agent Research System

An autonomous, multi-agent AI research platform with human-in-the-loop oversight, structured task planning, topological wave execution, live progress tracking, and comprehensive report generation backed by verified web citations.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [How to Run](#how-to-run)
  - [1. Database Setup](#1-database-setup)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
- [Running Tests](#running-tests)
- [API Reference](#api-reference)
- [License](#license)

---

## Overview

The **Multi-Agent Research System** transforms an open-ended research question into a comprehensive, publication-ready research report. Instead of relying on a single monolithic prompt, it employs specialized AI agents collaborating in a structured, observable workflow:

1. **Plan & Decompose**: Analyzes the query, establishes research hypotheses, outlines scope, and generates discrete, typed subtasks with dependency graphs (DAG).
2. **Human Approval**: Pauses for user review before running expensive searches. Users can inspect subtasks, request prompt-assisted plan revisions, or approve execution.
3. **Parallel Wave Execution**: Resolves dependencies topologically and executes independent tasks concurrently using autonomous web researcher agents.
4. **Synthesis & Lead Editing**: Consolidates gathered evidence, cross-checks findings, and synthesizes a structured markdown report with grounded citations.

---

## Key Features

### 🤖 Multi-Agent Orchestration
- **Research Planner**: Formulates comprehensive investigation outlines, objectives, and research dimensions.
- **Task Architect**: Breaks down the plan into typed subtasks (`research` vs `synthesis`) with bounded scopes, precise target questions, search budgets, and source requirements.
- **Task Researchers**: Autonomous subagents equipped with budgeted web search (`search_web` via Tavily) and full-page text extraction (`fetch_page`) to investigate specific angles.
- **Lead Editor & Section Writers**: Hierarchical report compilation pipeline that groups findings by section and weaves them into a cohesive final synthesis.

### 🛡️ Human-in-the-Loop (HITL) Control
- Sessions start in `PENDING_APPROVAL` status immediately upon plan and task generation.
- **Interactive Plan Revision**: Users can submit feedback to re-architect tasks and adjust focus prior to execution.
- **1-Click Execution & Graceful Cancellation**: Users trigger execution when satisfied, with the ability to cancel running tasks at any point.

### ⚡ Topological Wave Execution Pipeline
- Resolves subtask `depends_on` relationships into sequential execution waves.
- Tasks within the same wave run in parallel (`asyncio.gather`), while dependent synthesis tasks wait for upstream research findings.
- **Search Budget Caps**: Configurable query quotas per subtask prevent runaway tool loops and enforce source diversity.

### 🔍 Grounded Evidence & Source Inspection
- Automatic extraction and verification of citations (`[S1]`, `[S2]`, etc.) directly from findings.
- Source metadata tracking: URLs, publication dates, publishers, and snippet context.
- Dedicated source inspector drawer in the UI to explore evidence backing every claim.

### 🖥️ Modern Interactive UI
- **AI Workspace**: Responsive split-layout with collapsible session history, status filters, and batch management.
- **Live Pipeline View**: Real-time wave progression monitoring and streaming dispatch event logs.
- **Report Reader**: Distraction-free typography, auto-generated Table of Contents, and 1-click Markdown export.

---

## System Architecture

```mermaid
flowchart TD
    User([User / Client])
    
    subgraph Frontend ["Frontend (React 19 + Vite)"]
        UI["Workspace UI / Session Manager"]
        PlanReview["Plan Review & Revision Modal"]
        PipelineView["Live Wave Pipeline & Logs"]
        ReportViewer["Report Reader & Source Inspector"]
    end

    subgraph Backend ["Backend (FastAPI)"]
        API["REST API Router (/api/v1/researches)"]
        Service["Research Service"]
        DB[(PostgreSQL)]
    end

    subgraph AgentSystem ["Multi-Agent Research Engine"]
        Planner["Planner Agent (Gemini)"]
        Architect["Task Architect (Gemini)"]
        Dispatcher["Wave Dispatcher"]
        subgraph Workers ["Concurrent Task Agents"]
            Agent1["Task Researcher 1"]
            Agent2["Task Researcher 2"]
            AgentN["Task Researcher N"]
        end
        Tavily["Tavily Search API"]
        ReportWriter["Lead Editor & Section Writers"]
    end

    User <--> UI
    UI <--> API
    API <--> Service
    Service <--> DB
    
    Service --> Planner
    Planner --> Architect
    Architect --> DB
    
    User -- "Approve / Revise" --> API
    Service --> Dispatcher
    Dispatcher --> Workers
    Workers <--> Tavily
    Workers --> DB
    Dispatcher --> ReportWriter
    ReportWriter --> DB
    DB --> ReportViewer
```

---

## Tech Stack

### Backend
- **Language & Runtime**: Python 3.13+
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (fast Python package and project manager)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) with asynchronous request handlers and background tasks
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **LLM Orchestration**: [LangChain](https://www.langchain.com/) & [LangChain Google GenAI](https://github.com/langchain-ai/langchain-google) (Google Gemini models)
- **Search Tooling**: [Tavily Python SDK](https://tavily.com/) for real-time web search and page content extraction
- **Database & ORM**: PostgreSQL with [SQLAlchemy 2.0 (asyncio)](https://www.sqlalchemy.org/) and [asyncpg](https://github.com/MagicStack/asyncpg)
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)

### Frontend
- **Framework**: [React](https://react.dev/) with [TypeScript](https://www.typescriptlang.org/)
- **Bundler & Dev Server**: [Vite](https://vitejs.dev/) / [Bun](https://bun.sh/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) & [@tailwindcss/typography](https://tailwindcss.com/docs/typography-plugin)
- **UI Components**: [Radix UI](https://www.radix-ui.com/) accessible primitives & [Lucide React](https://lucide.dev/) icons
- **State Management**: [TanStack React Query](https://tanstack.com/query) (server cache & polling) and [Zustand](https://github.com/pmndrs/zustand) (client UI state)
- **Markdown Rendering**: `react-markdown` with `remark-gfm`

---

## Project Structure

```text
research_system/
├── alembic/                      # Database migrations
│   ├── env.py
│   └── versions/                 # Migration version scripts
├── apps/
│   ├── api/                      # FastAPI application layer
│   │   ├── main.py               # Application entry point & CORS
│   │   ├── router.py             # Research session endpoints
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── db/                       # Database models & configuration
│   │   ├── database.py           # Async engine & session factories
│   │   └── models.py             # SQLAlchemy models (Sessions, Plans, Tasks, Reports)
│   └── research_agent/           # Core agent logic
│       ├── cancellation.py       # Async cancellation token management
│       ├── dispatcher.py         # Topological wave resolution & task execution
│       ├── planner.py            # Plan creation & revision agents
│       ├── prompts.py            # System prompts for all agents
│       ├── report_writer.py      # Lead editor & section synthesizer
│       ├── service.py            # High-level business logic orchestration
│       ├── task_agent.py         # Individual subtask researcher
│       ├── task_architect.py     # Subtask generation & DAG parser
│       ├── tools.py              # Tavily web search & page scraping tools
│       └── utils.py              # LLM factory & transient error handling
├── frontend/                     # React + Vite TypeScript frontend
│   ├── src/
│   │   ├── api/                  # API client & endpoint definitions
│   │   ├── components/           # UI components & research modules
│   │   ├── hooks/                # React Query hooks
│   │   ├── store/                # Zustand UI store
│   │   └── App.tsx               # Main application container
│   ├── package.json
│   └── vite.config.ts
├── tests/                        # Backend test suite (pytest)
│   ├── test_api_endpoints.py
│   ├── test_dispatcher.py
│   ├── test_report_writer.py
│   ├── test_service_db_integration.py
│   └── ...
├── main.py                       # Root launcher for backend
├── pyproject.toml                # Python dependencies & tools config
└── README.md
```

---

## Prerequisites

Before running the project, ensure you have installed:

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or `pip`
- **PostgreSQL 14+** (running locally or accessible via network)
- **[Bun](https://bun.sh/)** (recommended) or **Node.js 18+** with `npm`
- **API Keys**:
  - [Google AI Studio API Key](https://aistudio.google.com/) for Gemini models
  - [Tavily API Key](https://tavily.com/) for web search and page extraction

---

## Environment Configuration

Create a `.env` file in the project root by copying the template below:

```bash
# Database URL (PostgreSQL with asyncpg driver)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/research_system

# Gemini API Key (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# Default Gemini Model (used by planner, task architect, and report writer)
GEMINI_PLANNER_MODEL=gemini-3.7-flash

# Optional: Role-specific model overrides
# GEMINI_ARCHITECT_MODEL=gemini-3.7-flash
# GEMINI_TASK_MODEL=gemini-3.7-flash
# GEMINI_REPORT_MODEL=gemini-3.7-flash

# Tavily API Key (Required for live web search and scraping)
TAVILY_API_KEY=your_tavily_api_key_here
```

---

## How to Run

### 1. Database Setup

Ensure PostgreSQL is running and create the database:

```bash
# Using PostgreSQL CLI
psql -U postgres -c "CREATE DATABASE research_system;"
```

Apply the database migrations using Alembic:

```bash
uv run alembic upgrade head
```

---

### 2. Backend Setup

1. **Install Python dependencies**:
   ```bash
   uv sync
   ```

2. **Start the FastAPI backend server**:
   ```bash
   uv run python main.py
   ```
   *Alternatively, using uvicorn directly:*
   ```bash
   uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Verify backend**:
   - Health check: `http://localhost:8000/health`
   - Interactive Swagger API documentation: `http://localhost:8000/docs`
   - OpenAPI specification: `http://localhost:8000/openapi.json`

---

### 3. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   bun install
   # or: npm install
   ```

3. **Start the Vite development server**:
   ```bash
   bun run dev
   # or: npm run dev
   ```

4. **Open the application**:
   - Access the web interface at **`http://localhost:5173`**.
   - API calls to `/api/*` are automatically proxied to the backend at `http://localhost:8000`.

---

## Running Tests

The test suite covers API endpoints, database operations, agent orchestration, report generation, and error resilience.

To run the backend test suite:

```bash
# Run all tests
uv run pytest

# Run with verbose output and test names
uv run pytest -v

# Run a specific test module
uv run pytest tests/test_api_endpoints.py
```

To build or validate the frontend:

```bash
cd frontend
bun run build
# or: npm run build
```

---

## API Reference

The FastAPI backend exposes the following primary endpoints under `/api/v1/researches`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/researches` | List all research sessions with optional status filter and pagination. |
| `POST` | `/api/v1/researches` | Create a new research session, generate plan & subtasks (`PENDING_APPROVAL`). |
| `GET` | `/api/v1/researches/{id}` | Retrieve research session details (plan, subtasks, logs, and report). |
| `PUT` | `/api/v1/researches/{id}` | Revise research plan and re-architect tasks based on user feedback. |
| `POST` | `/api/v1/researches/{id}/start` | Approve research plan and launch background wave execution (`RUNNING`). |
| `POST` | `/api/v1/researches/{id}/cancel` | Cancel an in-progress or pending research session (`CANCELLED`). |
| `DELETE`| `/api/v1/researches/{id}` | Permanently delete a research session and all associated data. |
| `POST` | `/api/v1/researches/batch-delete`| Batch delete multiple research sessions by ID list. |
| `GET` | `/api/v1/researches/{id}/tasks` | Retrieve all subtasks for a specific research session. |
| `GET` | `/api/v1/researches/{id}/tasks/{task_id}` | Retrieve details for a specific subtask (findings, sources, status). |
| `GET` | `/health` | Health check endpoint returning service status. |

Interactive API documentation and schema explorers are available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## License

This project is licensed under the MIT License.
