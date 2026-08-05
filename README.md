# smartlog

Bu repository ana uygulamayi `log-parser-engine/` altinda tutar.

## Backend Kurulum ve Calistirma

```bash
cd log-parser-engine
poetry install
poetry run uvicorn log_parser_engine.api.main:app --reload --port 8000
```

## Backend Test, Lint ve Typecheck

```bash
cd log-parser-engine
poetry run pytest
poetry run pytest --cov
poetry run ruff check
poetry run mypy src
poetry build
```

## Frontend Kurulum ve Calistirma

```bash
cd log-parser-engine/frontend
npm ci
npm run dev
```

## Frontend Test, Lint, Typecheck ve Build

```bash
cd log-parser-engine/frontend
npm run typecheck
npm run lint
npm run test
npm run build
```