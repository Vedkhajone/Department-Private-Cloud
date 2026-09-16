"""
Deterministic website type/framework detection.

No AI/LLM is involved (deliberately -- see docs/WEBSITE-HOSTING.md).
Detection looks only at the presence of specific, well-known files.
Anything ambiguous is rejected with a clear, actionable error rather
than guessed at -- a wrong guess here would mean either failing to
deploy a valid app or, worse, running something in a way its author
didn't intend.
"""

import json
from pathlib import Path

from fastapi import HTTPException, status

from app.models.website import WebsiteFramework, WebsiteType

_SUPPORTED_ERROR = (
    "Could not determine website type. Supported: static HTML "
    "(index.html at the ZIP root), a built React/Vite app "
    "(dist/index.html), Flask or FastAPI (requirements.txt plus "
    "app.py or main.py), or Node.js (package.json with a \"start\" script)."
)


def detect(root: Path) -> tuple[WebsiteType, WebsiteFramework, Path]:
    """
    Inspect the extracted project at `root` and return
    (type, framework, effective_root) -- effective_root is the
    directory that should actually be deployed/served (e.g. `dist/`
    for a built React app; `root` itself otherwise).
    """
    requirements = root / "requirements.txt"
    package_json = root / "package.json"

    if requirements.is_file():
        text = requirements.read_text(errors="ignore").lower()
        entry = _first_existing(root, ["app.py", "main.py"])

        if "fastapi" in text:
            if entry is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "requirements.txt lists FastAPI but no app.py or main.py entry point was found",
                )
            return WebsiteType.dynamic, WebsiteFramework.fastapi, root

        if "flask" in text:
            if entry is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "requirements.txt lists Flask but no app.py or main.py entry point was found",
                )
            return WebsiteType.dynamic, WebsiteFramework.flask, root

    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(errors="ignore"))
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "package.json is not valid JSON")

        if not isinstance(data, dict) or "start" not in data.get("scripts", {}):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'package.json must define a "start" script (npm start) for Node.js deployment',
            )
        return WebsiteType.dynamic, WebsiteFramework.node, root

    if (root / "index.html").is_file():
        return WebsiteType.static, WebsiteFramework.html, root

    if (root / "dist" / "index.html").is_file():
        return WebsiteType.static, WebsiteFramework.react, root / "dist"

    raise HTTPException(status.HTTP_400_BAD_REQUEST, _SUPPORTED_ERROR)


def _first_existing(root: Path, names: list[str]) -> Path | None:
    for candidate in names:
        p = root / candidate
        if p.is_file():
            return p
    return None
