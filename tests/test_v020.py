"""Tests for v0.2.0 features: auth, ssl, filter, custom headers."""

import os
import subprocess
import sys


PYTEST = [sys.executable, "-m", "pytest"]


def test_auth_header_passed_to_case(tmp_path):
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

    test_file = tmp_path / "test_auth.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.headers.get("Authorization") == "Bearer secret123"
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-auth", "Authorization: Bearer secret123",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout


def test_skip_ssl_flag(tmp_path):
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

    test_file = tmp_path / "test_ssl.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.verify_ssl is False
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-skip-ssl",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout


def test_filter_by_method(tmp_path):
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
    post:
      operationId: createItem
      responses:
        "201":
          description: created
""", encoding="utf-8")

    test_file = tmp_path / "test_filter.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.method == "GET"
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-filter", "GET",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout
    assert "1 passed" in result.stdout


def test_filter_by_method_and_path(tmp_path):
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
  /items:
    get:
      operationId: getItems
      responses:
        "200":
          description: ok
""", encoding="utf-8")

    test_file = tmp_path / "test_filter2.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.path == "/users"
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-filter", "GET:/users",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout
    assert "1 passed" in result.stdout


def test_filter_no_match_skips(tmp_path):
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

    test_file = tmp_path / "test_nomatch.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    pass
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-filter", "POST",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "skipped" in result.stdout.lower()


def test_custom_headers(tmp_path):
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

    test_file = tmp_path / "test_headers.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    assert contract_case.headers.get("X-API-Key") == "mykey"
    assert contract_case.headers.get("X-Region") == "us-east"
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", str(spec),
            "--contract-header", "X-API-Key: mykey",
            "--contract-header", "X-Region: us-east",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "PASSED" in result.stdout


def test_missing_spec_file_skips(tmp_path):
    test_file = tmp_path / "test_missing.py"
    test_file.write_text("""\
def test_endpoint(contract_case):
    pass
""", encoding="utf-8")

    result = subprocess.run(
        PYTEST + [
            "--contract-spec", "nonexistent.yaml",
            "-v", str(test_file),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert "skipped" in result.stdout.lower()