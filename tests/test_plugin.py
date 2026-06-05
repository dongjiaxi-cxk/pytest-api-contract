"""Tests for the pytest plugin integration (via subprocess)."""

import subprocess
import sys


PYTEST = [sys.executable, "-m", "pytest"]


def test_help_shows_contract_spec_option():
    result = subprocess.run(PYTEST + ["--help"], capture_output=True, text=True)
    assert "--contract-spec" in result.stdout


def test_help_shows_contract_base_url_option():
    result = subprocess.run(PYTEST + ["--help"], capture_output=True, text=True)
    assert "--contract-base-url" in result.stdout


def test_contract_marker_registered():
    result = subprocess.run(PYTEST + ["--markers"], capture_output=True, text=True)
    assert "contract" in result.stdout


def test_generates_parametrized_tests(tmp_path):
    spec = tmp_path / "api.yaml"
    spec.write_text("""\
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
servers:
  - url: http://localhost:9999
paths:
  /items:
    get:
      operationId: getItems
      responses:
        "200":
          description: ok
""", encoding="utf-8")

    test_file = tmp_path / "test_api.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.method == "GET"
    assert contract_case.path == "/items"
    assert contract_case.base_url == "http://localhost:9999"
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + ["--contract-spec", str(spec), "-v", str(test_file)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout
    assert "test_endpoint" in result.stdout


def test_skips_without_spec(tmp_path):
    test_file = tmp_path / "test_skip.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    pass
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + ["-v", str(test_file)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    # Test is skipped at collection time (no --contract-spec)
    assert "skipped" in result.stdout.lower()


def test_base_url_override(tmp_path):
    spec = tmp_path / "api.yaml"
    spec.write_text("""\
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
servers:
  - url: http://localhost:9999
paths:
  /items:
    get:
      operationId: getItems
      responses:
        "200":
          description: ok
""", encoding="utf-8")

    test_file = tmp_path / "test_override.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.base_url == "https://override.example.com"
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-base-url", "https://override.example.com",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout


def test_case_ids_are_descriptive(tmp_path):
    spec = tmp_path / "api.yaml"
    spec.write_text("""\
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
servers:
  - url: http://localhost:9999
paths:
  /users:
    get:
      operationId: getUsers
      responses:
        "200":
          description: ok
""", encoding="utf-8")

    test_file = tmp_path / "test_ids.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    pass
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + ["--contract-spec", str(spec), "-v", str(test_file)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "GET /users" in result.stdout