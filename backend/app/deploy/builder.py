"""
Controlled Docker image build inputs for dynamic deployments.

A student-supplied Dockerfile, if the ZIP contains one, is NEVER used
-- DECP always generates the Dockerfile itself from one of these three
fixed, trusted templates. This is what prevents a student from
injecting arbitrary `FROM`/`RUN`/`VOLUME` instructions into the image
build (see docs/WEBSITE-HOSTING.md, "Controlled image builds").
"""

from pathlib import Path

from app.models.website import WebsiteFramework

# The fixed port each template's app listens on inside its container.
# Never student-chosen -- see app/deploy/containers.py for how the
# backend reaches the container without publishing this to the host.
INTERNAL_PORTS: dict[WebsiteFramework, int] = {
    WebsiteFramework.flask: 5000,
    WebsiteFramework.fastapi: 8000,
    WebsiteFramework.node: 3000,
}

_FLASK_TEMPLATE = """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "{entry}"]
"""

_FASTAPI_TEMPLATE = """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir uvicorn
COPY . .
EXPOSE 8000
CMD ["uvicorn", "{module}:app", "--host", "0.0.0.0", "--port", "8000"]
"""

_NODE_TEMPLATE = """\
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev || npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""

_DEFAULT_DOCKERIGNORE = "node_modules\n__pycache__\n.git\nDockerfile\n"


def write_dockerfile(build_dir: Path, framework: WebsiteFramework) -> None:
    """
    Write a DECP-controlled Dockerfile into `build_dir`, overwriting
    anything a student may have included in their ZIP.
    """
    if framework == WebsiteFramework.flask:
        entry = "app.py" if (build_dir / "app.py").is_file() else "main.py"
        content = _FLASK_TEMPLATE.format(entry=entry)
    elif framework == WebsiteFramework.fastapi:
        module = "app" if (build_dir / "app.py").is_file() else "main"
        content = _FASTAPI_TEMPLATE.format(module=module)
    elif framework == WebsiteFramework.node:
        content = _NODE_TEMPLATE
    else:
        raise ValueError(f"No Docker template for framework: {framework}")

    (build_dir / "Dockerfile").write_text(content)

    dockerignore = build_dir / ".dockerignore"
    if not dockerignore.exists():
        dockerignore.write_text(_DEFAULT_DOCKERIGNORE)
