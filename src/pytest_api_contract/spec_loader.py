"""Load and parse OpenAPI 3.x specification files with env var support."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from .test_generator import resolve_env_in_dict


class SpecLoader:
    """Loads an OpenAPI spec, resolves env vars, and extracts endpoints."""

    def __init__(self, spec_path: str) -> None:
        self.spec_path: Path = Path(spec_path)
        self.spec: dict = self._load_spec()

    def _load_spec(self) -> dict:
        content: str = self.spec_path.read_text(encoding="utf-8")
        if self.spec_path.suffix in (".yaml", ".yml"):
            raw: dict = yaml.safe_load(content)
        elif self.spec_path.suffix == ".json":
            raw = json.loads(content)
        else:
            raise ValueError(f"Unsupported spec format: {self.spec_path.suffix}")
        return resolve_env_in_dict(raw)

    def get_base_url(self) -> str:
        servers: list = self.spec.get("servers", [])
        if servers:
            return servers[0]["url"]
        return ""

    def get_endpoints(self) -> list[dict]:
        endpoints: list[dict] = []
        paths: dict = self.spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation: dict | None = path_item.get(method)
                if operation:
                    endpoints.append({
                        "method": method.upper(),
                        "path": path,
                        "operation_id": operation.get("operationId", ""),
                        "parameters": operation.get("parameters", []),
                        "request_body": operation.get("requestBody"),
                        "responses": operation.get("responses", {}),
                    })

        return endpoints
