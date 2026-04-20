# PaperTrail

**Agentic document processing pipeline for Indian financial documents.**

PaperTrail processes documents through classification, multi-pass extraction, validation, correction, and decision — with full traceability and human-in-the-loop checkpoints.

## Supported Document Types

- Indian Cheque
- Indian Bank Statement
- Indian Salary Slip
- Indian ITR Form

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- PostgreSQL 15 or 16
- [uv](https://docs.astral.sh/uv/) package manager
- OpenRouter API key

### Setup

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Copy env template and configure
cp .env.example .env
# Edit .env with your API keys

# Start PostgreSQL
docker compose up -d postgres

# Apply migrations
papertrail db migrate

# Seed playbooks and tools
papertrail db seed

# Verify setup
papertrail playbook list
```

### Run a Document

```bash
papertrail run cheque_sample.jpg --playbook indian_cheque
```

### CLI Commands

```
papertrail run <file> --playbook <slug>    Process a document
papertrail playbook list                    List playbooks
papertrail playbook show <slug>             Show merged config
papertrail runs list                        List recent runs
papertrail runs show <run-uid>              Show run details
papertrail hitl list                        Show pending HITL items
papertrail hitl resolve <run-uid>           Resolve a checkpoint
papertrail db migrate                       Apply migrations
papertrail db seed                          Seed playbooks
```

## Architecture

```
CLI / REST API / Streamlit UI
        │
  LangGraph State Machine
  (preupload → classify → pass_a → pass_b → pass_c → pass_d → decide → act)
        │
  ┌─────┼─────┬──────┐
  Engines  LLM  Validation  Tools
        │
  PostgreSQL + Blob Storage + Langfuse
```

See [docs/PaperTrail_Technical_Documentation.md](docs/PaperTrail_Technical_Documentation.md) for the full specification.

## Development

```bash
# Run unit tests
pytest tests/unit/

# Run with coverage
pytest tests/unit/ --cov=papertrail

# Lint and format
ruff check .
ruff format .

# Type check
mypy papertrail/
```

## Team

**Team Twenty** · Almichael · Anuj · Rajesh · Swati
