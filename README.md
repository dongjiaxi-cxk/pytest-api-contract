# pytest-api-contract

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/pytest-plugin-orange.svg)](https://docs.pytest.org/)
[![CI](https://github.com/dongjiaxi-cxk/pytest-api-contract/actions/workflows/tests.yml/badge.svg)](https://github.com/dongjiaxi-cxk/pytest-api-contract/actions/workflows/tests.yml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-45%20passed-brightgreen.svg)](tests/)
[![PyPI](https://img.shields.io/badge/pypi-v0.3.0-blue.svg)](https://pypi.org/project/pytest-api-contract/)

**pytest plugin for API contract testing.** Point it at an OpenAPI 3.x spec, and pytest auto-generates parametrized test cases for every endpoint.

```bash
pytest --contract-spec openapi.yaml -v
```

```
test_api.py::test_endpoint[GET /users] PASSED
test_api.py::test_endpoint[POST /users] PASSED
test_api.py::test_endpoint[GET /users/{userId}] PASSED
```

## Why this exists

Most API testing tools are standalone CLIs. This one integrates directly into pytest — your existing test runner. Benefits:
- **Zero learning curve** for pytest users
- **CI-native** — runs anywhere pytest runs
- **Parametrized** — one test function, N test cases (one per endpoint)
- **Assertions** — status code, schema, response time, JSONPath, snapshots

## Quick Start

```bash
pip install pytest-api-contract
```

Write a test file:
```python
# test_api.py
def test_api_endpoint(contract_case):
    result = contract_case.execute()
    assert result["passed"], "\n".join(result.get("messages", []))
```

Run:
```bash
pytest test_api.py --contract-spec openapi.yaml -v
```

## Features

| Feature | Flag | Description |
|---------|------|-------------|
| OpenAPI 3.x | `--contract-spec` | YAML/JSON spec file |
| Auth | `--contract-auth` | `"Bearer: $TOKEN"` auto-resolved from env |
| Filter | `--contract-filter` | `"GET:/users*"` or `"POST"` |
| SSL | `--contract-skip-ssl` | Disable certificate verification |
| Headers | `--contract-header` | Custom headers (repeatable) |
| Performance | `--contract-max-response-ms` | Fail if response exceeds N ms |
| JSONPath | `--contract-assert-jsonpath` | `"$.status:success"` |
| Snapshot | `--contract-snapshot-dir` | Save/compare response snapshots |
| Base URL | `--contract-base-url` | Override spec server URL |

## Advanced Usage

```bash
pytest test_api.py \
  --contract-spec openapi.yaml \
  --contract-auth "Bearer: $API_TOKEN" \
  --contract-header "X-Region: us-east" \
  --contract-filter "GET:/users*" \
  --contract-max-response-ms 500 \
  --contract-assert-jsonpath "$.status:success" \
  --contract-snapshot-dir ./snapshots \
  --contract-skip-ssl \
  -v
```

## How It Works

```
OpenAPI Spec
     |
     v
SpecLoader  -->  parses YAML/JSON, resolves ${ENV_VARS}
     |
     v
TestGenerator --> creates TestCase objects (method, path, params, body, schema)
     |
     v
pytest_generate_tests --> parametrizes "contract_case" fixture
     |
     v
Your test function receives each TestCase
     |
     v
TestCase.execute() --> HTTP request + status/schema/time/JSONPath/snapshot validation
```

## Project Structure

```
pytest-api-contract/
  src/pytest_api_contract/
    plugin.py          # pytest hooks + JSONPath resolver + snapshot engine
    spec_loader.py     # OpenAPI 3.x parser with env var support
    test_generator.py  # TestCase dataclass with execute() method
  tests/               # 45 pytest tests (unit + integration via subprocess)
  examples/
    petstore.yaml      # Real-world example spec
    test_petstore.py   # Real-world test file
```

## Running Tests

```bash
pip install -e .
pytest tests/ -v
```

## License

MIT