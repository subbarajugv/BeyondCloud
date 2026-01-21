# BeyondCloud Development Rules

## Architecture
- **Dual Backend**: Python (FastAPI) + Node.js (Express) - BOTH must be updated for shared features
- **Frontend**: SvelteKit with Svelte 5 runes mode
- **Database**: PostgreSQL with pgvector extension

## Code Standards

### Python Backend
- Use `uv pip install` for dependencies (not pip)
- All new modules must have corresponding tests in `tests/`
- Run locally: `source .venv/bin/activate && python main.py`
- Type hints required, use `mypy` for checking
- Format with `black`, lint with `ruff`

### Node.js Backend  
- TypeScript required
- Run locally: `npm run dev`
- ESLint for linting, `tsc --noEmit` for type checking

### Frontend
- Svelte 5 runes mode (`$state`, `$derived`, `$effect`)
- Run locally: `npm run dev`

## Enterprise Features
- **Secrets**: Use `SecretManager` interface, not raw `os.getenv()`
- **Logging**: Use `get_logger(__name__)`, not `print()`
- **Tracing**: Use `@traced` decorator or `create_span()` for important operations
- **Audit**: Use `siem_logger.log()` for security-relevant events

## Environment Variables
- `SECRET_BACKEND`: env | vault | aws
- `OTEL_ENABLED`: true | false
- `SIEM_ENABLED`: true | false
- Default to disabled/env for development

## Testing
- Python: `PYTHONPATH=. pytest tests/ -v`
- Node.js: `npm test`
- Always run tests before committing

## Before PR
1. Run CI checks locally:
   - `ruff check app/`
   - `black --check app/`
   - `mypy app/ --ignore-missing-imports`
   - `pytest tests/ -v`
2. Ensure both Python AND Node.js implementations are in sync

## CI/CD Platforms
We support multiple platforms - use the appropriate config:

| Platform | Config File |
|----------|-------------|
| **GitHub Actions** | `.github/workflows/ci.yml` |
| **GitLab CI/CD** | `.gitlab-ci.yml` |
| **Azure DevOps** | `azure-pipelines.yml` |
| **AWS CodeBuild** | `buildspec.yml` |

All configs run the same checks: lint, security scan, tests, build.
