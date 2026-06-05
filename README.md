# pytest-api-contract

[![tests](https://github.com/dongjiaxi-cxk/pytest-api-contract/actions/workflows/tests.yml/badge.svg)](https://github.com/dongjiaxi-cxk/pytest-api-contract/actions/workflows/tests.yml)

pytest plugin that turns an OpenAPI 3.x spec into parametrized API contract tests.

## How it works

- Reads an OpenAPI 3.x spec (YAML or JSON)
- Auto-generates one test case per endpoint (method + path + params + body)
- Parametrizes your test function so pytest runs each endpoint as a separate case
- Validates status codes, response time, Content-Type, and JSON Schema

## Install

```bash
pip install git+https://github.com/dongjiaxi-cxk/pytest-api-contract.git
```

Or locally:

```bash
pip install -e .
```

## Usage

Write a test file that accepts the `contract_case` fixture:

```python
# test_api.py
def test_api_endpoint(contract_case):
    result = contract_case.execute()
    assert result["passed"], "\n".join(result.get("messages", []))
```

Run with your OpenAPI spec:

```bash
pytest test_api.py --contract-spec openapi.yaml -v
```

Output:

```
test_api.py::test_api_endpoint[GET /users] PASSED
test_api.py::test_api_endpoint[POST /users] PASSED
test_api.py::test_api_endpoint[GET /users/{userId}] PASSED
```

## Options

| Option | Description |
|--------|-------------|
| `--contract-spec PATH` | Path to OpenAPI 3.x spec (YAML/JSON) |
| `--contract-base-url URL` | Override the base URL from spec |

## Example

See `examples/petstore.py` and `examples/petstore.yaml` for a real-world example against the Swagger Petstore API.

```bash
pytest examples/test_petstore.py --contract-spec examples/petstore.yaml -v
```

## Project structure

```
pytest-api-contract/
  src/pytest_api_contract/
    __init__.py
    plugin.py          # pytest hooks: addoption, configure, generate_tests
    spec_loader.py     # OpenAPI 3.x parser
    test_generator.py  # TestCase dataclass + generator
  tests/
    fixtures/
      test_api.yaml    # test fixture spec
    test_spec_loader.py
    test_test_generator.py
    test_plugin.py     # integration tests (subprocess)
  examples/
    petstore.yaml
    test_petstore.py
```

## License

MIT