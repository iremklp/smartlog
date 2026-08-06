from __future__ import annotations

from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SinglePageStaticFiles(StaticFiles):
    """Serve static files and fall back to index.html for SPA routes."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise

        if "." in path:
            raise HTTPException(status_code=404)

        return await super().get_response("index.html", scope)


def resolve_frontend_dist(*, mode: str, env_path: str | None = None) -> Path | None:
    """Return a usable frontend dist path, depending on configured mode."""

    if mode == "api-only":
        return None

    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path).expanduser())
    else:
        project_root = Path(__file__).resolve().parents[3]
        candidates.append(project_root / "dist")

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate

    if mode == "require":
        raise RuntimeError("frontend dist is required but not found")
    return None
