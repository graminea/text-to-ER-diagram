# Text to ER

Natural-language requirements to validated conceptual ER schemas.

## Architecture
- `backend/app/er/models.py` defines the canonical Pydantic ER contract; `app.domain` re-exports it.
- `generations/service.py` orchestrates provider → parse → deterministic validation → typed storage.
- `generations/ports.py` defines injectable generator/storage boundaries; `providers.py` selects providers.
- `generations/adapters/` isolates SQLite, the single-call LLM flow, prompts and the removable demo.
- `entrypoints/http.py` owns HTTP mapping; `bootstrap.py` owns reusable assembly and lifecycle.
- Legacy flat modules remain compatibility exports; `app.main:app` remains the ASGI entry point.
- `backend/tests/test_dependencies.py` enforces import boundaries/cycles; see `docs/architecture.md`.
- `frontend/` uses React, TypeScript and React Flow (`@xyflow/react`).

## Invariants
- Never execute generated SQL. SQL export is outside this MVP.
- Treat provider output as untrusted. No LLM calls inside HTTP routes.
- Structural validity is not semantic correctness or human approval.
- Preserve assumptions and ambiguities; never hide mock limitations.
- Each relationship is binary. Recursive relationships need distinct role names.
- No secrets in source or logs. Real provider usage is opt-in and outside required CI.

## Commands (from repository root)
Create `.venv` and install `backend[dev]` as described in README.md.
- Backend: `cd backend`, then `python -m pytest`, `ruff check .`, `mypy`.
- Boundaries only: from `backend`, run `python -m pytest tests/test_dependencies.py -q`.
- Frontend: `cd frontend`, then `npm test`, `npm run build`.
- Browser flow: `cd frontend`, then `npm run test:e2e` (backend Python on PATH).

## Workflow
Read relevant code and docs; plan substantial work; deliver a small complete behavior.
Test observable behavior, inspect the diff, and report executed checks and limitations.

## UI Design Rules
- Favor functional minimalism over decorative design.
- Prioritize information density and clear visual hierarchy.
- Avoid unnecessary cards, containers, borders, badges, and section headers.
- No gradients, glassmorphism, excessive shadows, or decorative backgrounds.
- Do not add hero sections, KPI cards, or sidebars unless functionally necessary.
- Use compact spacing and restrained typography.
- Prefer simple tables, lists, and inline controls over nested cards.
- Every visible element must serve a specific user task.
- Remove redundant labels, descriptions, and repeated information.
- Follow the existing design system instead of inventing new patterns.
- Before implementing, identify elements that can be removed without harming usability.

## Design Priority
The rules in this file take precedence over
aesthetic suggestions from frontend-design.

Use frontend-design for visual quality, typography,
layout composition, and interaction design,
but always prioritize functional minimalism.

When in doubt, remove rather than add.
