"""Generate test cases from OpenAPI endpoint definitions."""

import os
import re
from dataclasses import dataclass, field

import os
import re
import requests
import jsonschema


_ENV_RE = re.compile(r"\$\{(\w+)\}|\$(\w+)")


def resolve_env(value: str) -> str:
    """Replace ${VAR} or $VAR with environment variable values."""
    def _replacer(m):
        name = m.group(1) or m.group(2)
        return os.environ.get(name, "")

    return _ENV_RE.sub(_replacer, value)


def resolve_env_in_dict(data: dict) -> dict:
    """Recursively resolve env vars in dict values."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = resolve_env(value)
        elif isinstance(value, dict):
            result[key] = resolve_env_in_dict(value)
        elif isinstance(value, list):
            result[key] = [
                resolve_env_in_dict(item) if isinstance(item, dict) else
                resolve_env(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


@dataclass
class TestCase:
    """A single API test case that can execute itself."""

    name: str
    method: str
    path: str
    base_url: str
    params: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    path_params: dict = field(default_factory=dict)
    body: dict | None = None
    expected_status: int = 200
    expected_content_type: str = ""
    response_schema: dict | None = None
    verify_ssl: bool = True

    def execute(self, timeout: int = 10) -> dict:
        """Run this test case and return a result dict with passed/messages."""
        resolved_path = self.path
        for key, value in self.path_params.items():
            resolved_path = resolved_path.replace("{" + key + "}", str(value))

        url = self.base_url.rstrip("/") + resolved_path
        result = {
            "name": self.name,
            "passed": False,
            "status_code": None,
            "response_time_ms": 0,
            "error": None,
            "messages": [],
        }

        try:
            response = requests.request(
                method=self.method,
                url=url,
                params=self.params,
                json=self.body,
                headers=self.headers,
                timeout=timeout,
                verify=self.verify_ssl,
            )
            result["status_code"] = response.status_code
            result["response_time_ms"] = round(response.elapsed.total_seconds() * 1000)

            if response.status_code == self.expected_status:
                result["messages"].append("[PASS] Status: {} (expected {})".format(
                    response.status_code, self.expected_status))
            else:
                result["messages"].append("[FAIL] Status: {} (expected {})".format(
                    response.status_code, self.expected_status))

            if result["response_time_ms"] > 2000:
                result["messages"].append(
                    "[WARN] Slow response: {}ms".format(result["response_time_ms"]))
            else:
                result["messages"].append(
                    "[PASS] Response time: {}ms".format(result["response_time_ms"]))

            if self.expected_content_type:
                ct = response.headers.get("Content-Type", "")
                if self.expected_content_type in ct:
                    result["messages"].append("[PASS] Content-Type: " + ct)
                else:
                    result["messages"].append("[FAIL] Content-Type: " + ct)

            if self.response_schema:
                try:
                    body = response.json()
                    jsonschema.validate(instance=body, schema=self.response_schema)
                    result["messages"].append("[PASS] Response body matches schema")
                except jsonschema.ValidationError as e:
                    result["messages"].append(
                        "[FAIL] Schema: " + str(e.message)[:100])
                except ValueError:
                    result["messages"].append("[WARN] Not valid JSON, schema check skipped")

            # 5. Max response time threshold
            max_ms = getattr(self, "_max_response_ms", None)
            if max_ms and result["response_time_ms"] > max_ms:
                result["messages"].append(
                    "[FAIL] Response time: {}ms > {}ms threshold".format(
                        result["response_time_ms"], max_ms))

            # 6. JSONPath assertions
            jsonpath_asserts = getattr(self, "_jsonpath_asserts", [])
            if jsonpath_asserts:
                try:
                    body = response.json()
                    for jp_path, jp_expected in jsonpath_asserts:
                        from .plugin import _resolve_jsonpath
                        actual = _resolve_jsonpath(body, jp_path)
                        actual_str = str(actual)
                        if jp_expected in actual_str or jp_expected == actual_str:
                            result["messages"].append(
                                "[PASS] JSONPath {} = {}".format(jp_path, actual_str)[:80])
                        else:
                            result["messages"].append(
                                "[FAIL] JSONPath {} expected '{}', got '{}'".format(
                                    jp_path, jp_expected, actual_str)[:120])
                except ValueError:
                    result["messages"].append("[WARN] Not valid JSON, JSONPath check skipped")

            # 7. Snapshot testing
            snap_dir = getattr(self, "_snapshot_dir", None)
            if snap_dir:
                try:
                    body = response.json()
                    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", self.name)
                    snap_path = os.path.join(snap_dir, safe_name + ".json")
                    from .plugin import _snapshot_test
                    snap_ok, snap_msg = _snapshot_test(body, snap_path)
                    result["messages"].append(snap_msg)
                except ValueError:
                    result["messages"].append("[WARN] Not valid JSON, snapshot skipped")

            failures = [m for m in result["messages"] if m.startswith("[FAIL]")]
            result["passed"] = len(failures) == 0

        except requests.exceptions.Timeout:
            result["error"] = "Request timed out"
            result["messages"].append("[FAIL] " + result["error"])
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection failed"
            result["messages"].append("[FAIL] " + result["error"])
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            result["messages"].append("[FAIL] " + str(e))

        return result


class TestGenerator:
    """Generates test cases from OpenAPI spec endpoints."""

    def __init__(self, base_url: str, endpoints: list, default_headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.endpoints = endpoints
        self.default_headers = default_headers or {}

    def generate(self) -> list[TestCase]:
        test_cases = []

        for endpoint in self.endpoints:
            method = endpoint["method"]
            path = endpoint["path"]
            operation_id = endpoint["operation_id"] or f"{method}{path}"

            expected_status = 200
            response_schema = None
            responses = endpoint.get("responses", {})
            for status_code in responses:
                if status_code.startswith("2"):
                    expected_status = int(status_code)
                    response = responses[status_code]
                    content = response.get("content", {})
                    json_content = content.get("application/json", {})
                    response_schema = json_content.get("schema")
                    break

            params = {}
            path_params = {}
            for param in endpoint.get("parameters", []):
                if param.get("in") == "query" and param.get("required"):
                    params[param["name"]] = self._sample_value(param)
                elif param.get("in") == "path":
                    path_params[param["name"]] = self._sample_value(param)

            body = None
            request_body = endpoint.get("request_body")
            if request_body and method in ("POST", "PUT", "PATCH"):
                content = request_body.get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    body = self._generate_body(schema)

            test_cases.append(TestCase(
                name=operation_id,
                method=method,
                path=path,
                base_url=self.base_url,
                params=params,
                path_params=path_params,
                body=body,
                headers=dict(self.default_headers),
                expected_status=expected_status,
                response_schema=response_schema,
            ))

        return test_cases

    def _sample_value(self, param: dict):
        schema = param.get("schema", {})
        stype = schema.get("type", "string")
        if stype == "integer":
            return 1
        elif stype == "boolean":
            return "true"
        return "sample"

    def _generate_body(self, schema: dict) -> dict:
        if not schema or "properties" not in schema:
            return {}

        body = {}
        required_fields = schema.get("required", [])
        for field_name in required_fields:
            prop = schema["properties"].get(field_name, {})
            ptype = prop.get("type", "string")
            if ptype == "integer":
                body[field_name] = 1
            elif ptype == "string":
                body[field_name] = f"sample_{field_name}"
            elif ptype == "boolean":
                body[field_name] = False

        return body