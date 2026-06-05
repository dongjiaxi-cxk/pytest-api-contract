"""Load and parse OpenAPI 3.x specification files."""

import json
import yaml
from pathlib import Path


class SpecLoader:
    """Loads an OpenAPI spec and extracts endpoint information."""

    def __init__(self, spec_path: str):
        self.spec_path = Path(spec_path)
        self.spec = self._load_spec()

    def _load_spec(self) -> dict:
        content = self.spec_path.read_text(encoding="utf-8")
        if self.spec_path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        elif self.spec_path.suffix == ".json":
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported spec format: {self.spec_path.suffix}")

    def get_base_url(self) -> str:
        servers = self.spec.get("servers", [])
        if servers:
            return servers[0]["url"]
        return ""

    def get_endpoints(self) -> list[dict]:
        endpoints = []
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = path_item.get(method)
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