# Research System Frontend

Modern, modular React 19 frontend for the Multi-Agent Research System API.

## Features
- **AI Workspace Interface**: Collapsible session history sidebar, adaptive status filters, and multi-view workspace.
- **Human-in-the-Loop Review**: Review synthesized research plans and subtasks before execution, with prompt-assisted plan revisions.
- **Live Wave Execution Pipeline**: Real-time wave progression monitoring with adaptive polling (2s interval while `RUNNING`) and streaming dispatch logs.
- **Deep Report Reader & Source Inspector**: High-readability Markdown typography, auto-generated Table of Contents, grounded web citations drawer, and 1-click Markdown export.
- **Modern Standards**: Built with React 19, TypeScript, Tailwind CSS, Radix UI primitives, Lucide icons, and TanStack Query.

---

## Quick Start

### 1. Start the FastAPI Backend
From the root directory:
```bash
# Ensure PostgreSQL database is running
uv run python main.py
# Backend runs at http://localhost:8000
```

### 2. Start the Frontend
In the `frontend` directory:
```bash
cd frontend

# Install dependencies (if not already installed)
bun install

# Start Vite dev server with backend API proxy
bun run dev
```

The frontend will start at **`http://localhost:5173`** and proxy `/api/*` requests seamlessly to `http://localhost:8000`.

---

## Build for Production
```bash
bun run build
```
Build output is saved to `dist/`.
