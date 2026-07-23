# log-parser-engine

This project provides the initial scaffold for a plugin-oriented log parser engine.
The focus of this stage is project structure, dependency configuration, and a minimal smoke test. No parser implementations or runtime logic have been added yet.

## Purpose

The long-term goal is to build a flexible log analysis platform that can parse logs through extensible plugins and support future integrations such as APIs, queues, multiprocessing, and AI features.

## Installation

1. Make sure Python 3.11 is installed.
2. Install Poetry if it is not already available.
3. Run the following commands from the project root:

```bash
poetry install
```

## Running tests

```bash
poetry run pytest
```

## Linting

```bash
poetry run ruff check .
```

## Type checking

```bash
poetry run mypy src
```

## Plugin discovery notes

Parser implementation modules are separate from plugin entry modules. Webserver plugins are exposed only through `*_plugin.py` entry modules, and helper modules must not export `Parser` or `create_parser`.
