"""pytest plugin for API contract testing from OpenAPI specs.

Usage:
    pytest --contract-spec openapi.yaml
"""

import pytest

from .spec_loader import SpecLoader
from .test_generator import TestGenerator


def pytest_addoption(parser):
    group = parser.getgroup("api-contract")
    group.addoption(
        "--contract-spec",
        action="store",
        default=None,
        help="Path to OpenAPI 3.x spec file (YAML or JSON)",
    )
    group.addoption(
        "--contract-base-url",
        action="store",
        default=None,
        help="Override base URL from spec",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "contract: mark a test class or function as an API contract test",
    )


def pytest_generate_tests(metafunc):
    """Parametrize contract_case fixture for each endpoint in the spec."""
    if "contract_case" not in metafunc.fixturenames:
        return

    spec_path = metafunc.config.getoption("--contract-spec")
    if not spec_path:
        pytest.skip("--contract-spec not provided; cannot generate contract cases")

    override_url = metafunc.config.getoption("--contract-base-url")

    loader = SpecLoader(spec_path)
    base_url = override_url or loader.get_base_url()
    endpoints = loader.get_endpoints()
    generator = TestGenerator(base_url, endpoints)
    cases = generator.generate()

    ids = [f"{c.method} {c.path}" for c in cases]
    metafunc.parametrize("contract_case", cases, ids=ids)