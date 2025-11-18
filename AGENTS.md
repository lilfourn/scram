# Agent Guidelines

## Commands
- **Run**: `python main.py` (Verify entry point)
- **Test**: `pytest` (Single: `pytest path/to/test.py::test_name`)
- **Lint/Format**: `ruff check .` / `ruff format .`
- **Type Check**: `mypy .`

## Code Style
- **Stack**: Python 3.10+, Asyncio, Pydantic V2, Textual, LangGraph.
- **Style**: PEP 8 via Ruff. **Mandatory** type hints.
- **Imports**: Absolute imports. Group: stdlib, 3rd-party, local.
- **Errors**: Use specific exceptions; ensure graceful TUI failure.
- **Naming**: `snake_case` (vars/funcs), `PascalCase` (classes).

## Workflow & Memory
- **Docs**: Store all agent documents/specs in `@artifcacts/`.
- **Tasks**: Manage, write, and view tasks in `@artifcacts/tasks`.
- **Specs**: Strictly follow architecture in `@artifcacts/specs.md`.
