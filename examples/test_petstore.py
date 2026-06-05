"""Example: use pytest-api-contract to test a real API against its OpenAPI spec.

Run:
    pytest test_petstore.py --contract-spec examples/petstore.yaml
"""


def test_api_endpoint(contract_case):
    """Each endpoint in the spec becomes one parametrized test case."""
    result = contract_case.execute()
    assert result["passed"], "\n".join(result.get("messages", []))