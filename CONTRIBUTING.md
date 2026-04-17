# Contributing to TradeCRM

Thank you for your interest in contributing. This document covers the development setup, code standards, and contribution process.

---

## Development Setup

### Prerequisites

- Python 3.9+
- Node.js 20+
- Docker and Docker Compose (for PostgreSQL and Redis)
- Git

### Backend

```bash
cd app/backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your local settings

# Start PostgreSQL and Redis
docker compose up -d

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd app/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your Clerk publishable key and backend URL

# Start the development server
npm run dev
```

### Dev Mode

Set `DEV_MODE=true` in `app/backend/.env` to bypass Clerk authentication and use a hardcoded test user. This is useful for local development when you do not have Clerk credentials configured.

---

## Code Style

### Python (Backend)

- **Formatter/Linter**: [Ruff](https://github.com/astral-sh/ruff)
- **Line length**: 100 characters
- **Target version**: Python 3.9
- **Lint rules**: E, F, I, W (pyflakes, pycodestyle, isort, warnings)

Run the linter:

```bash
cd app/backend
ruff check .
ruff format .
```

Configuration is in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

### TypeScript (Frontend)

- **Linter**: ESLint with `eslint-config-next`
- **Framework**: Next.js 16 conventions

Run the linter:

```bash
cd app/frontend
npm run lint
```

### General Guidelines

- Use type hints in Python. All function parameters and return types should be annotated.
- Use TypeScript types in the frontend. Avoid `any` where possible.
- Write descriptive variable and function names. Avoid abbreviations except for common ones (db, id, url).
- Keep functions focused. If a function exceeds ~50 lines, consider splitting it.
- Add logging for important operations using the structured logger (`get_logger`).

---

## Branch Naming

Use the following conventions for branch names:

| Type | Format | Example |
|------|--------|---------|
| Feature | `feat/short-description` | `feat/campaign-ab-testing` |
| Bug fix | `fix/short-description` | `fix/enrichment-timeout` |
| Documentation | `docs/short-description` | `docs/api-reference` |
| Refactor | `refactor/short-description` | `refactor/agent-task-runner` |
| Chore | `chore/short-description` | `chore/upgrade-fastapi` |

---

## Commit Conventions

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): short description

Optional longer description.
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`

**Scopes**: `api`, `frontend`, `models`, `agents`, `integrations`, `enrichment`, `pipeline`, `campaigns`, `inbox`, `leads`, `catalog`

**Examples**:

```
feat(api): add bulk contact enrichment endpoint
fix(enrichment): handle Perplexity rate limit with retry
docs(connectors): add GupShup Direct API setup instructions
refactor(agents): extract step tracking into shared base class
test(api): add company CRUD integration tests
chore(deps): upgrade SQLAlchemy to 2.0.30
```

---

## Pull Request Process

1. **Create a branch** from `main` using the naming convention above
2. **Make your changes** with clear, focused commits
3. **Run linters** before pushing:
   ```bash
   cd app/backend && ruff check . && ruff format --check .
   cd app/frontend && npm run lint
   ```
4. **Run tests** if applicable:
   ```bash
   cd app/backend && pytest
   ```
5. **Push your branch** and open a pull request against `main`
6. **Fill in the PR template**:
   - Summary of what changed and why
   - How to test the changes
   - Screenshots for UI changes
7. **Address review feedback** with new commits (do not force-push during review)

### PR Review Checklist

- [ ] Code follows the project style guidelines
- [ ] All API endpoints include `tenant_id` scoping
- [ ] New database models include `tenant_id` column
- [ ] Sensitive data is not logged or exposed in API responses
- [ ] New features have corresponding API documentation comments
- [ ] No hardcoded secrets or credentials

---

## Database Migrations

When you change a model:

1. Make the model change in `app/backend/app/models/`
2. Generate a migration:
   ```bash
   cd app/backend
   alembic revision --autogenerate -m "description of change"
   ```
3. Review the generated migration in `alembic/versions/`
4. Apply it:
   ```bash
   alembic upgrade head
   ```
5. Commit both the model change and the migration file

---

## Adding a New API Endpoint

1. Create or modify a router file in `app/backend/app/api/`
2. Define Pydantic schemas in `app/backend/app/schemas/`
3. Include `tenant_id: CurrentTenantId` as a dependency parameter
4. Add the router to `app/backend/app/main.py` (if new file)
5. Add logging for significant operations

---

## Adding a New Integration

1. Create a service file in `app/backend/app/integrations/`
2. Add required env vars to `app/backend/app/config.py`
3. Add placeholder values to `app/backend/.env.example`
4. Document the integration in `docs/connectors.md`

---

## Issue Guidelines

When opening an issue:

- **Bug reports**: Include steps to reproduce, expected behavior, actual behavior, and relevant logs
- **Feature requests**: Describe the use case, proposed solution, and any alternatives considered
- **Questions**: Check existing documentation and issues first

Use labels: `bug`, `enhancement`, `documentation`, `question`, `good-first-issue`

---

## Project Structure Reference

See the [README](README.md) for the full project structure tree.
