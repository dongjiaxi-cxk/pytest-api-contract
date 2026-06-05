"""pytest plugin for API contract testing from OpenAPI specs.

Features:
    --contract-spec PATH     Path to OpenAPI 3.x spec
    --contract-base-url URL  Override base URL
    --contract-auth VAL      Auth header (e.g. "Bearer: token")
    --contract-skip-ssl      Disable SSL verification
    --contract-filter VAL    Filter endpoints (method:path pattern)
    --contract-header VAL    Custom header (key:value)

Usage:
    pytest --contract-spec openapi.yaml -v
    pytest --contract-spec openapi.yaml --contract-auth "Bearer: $TOKEN"
    pytest --contract-spec openapi.yaml --contract-filter "GET:/users" --contract-skip-ssl
"""

import os
import fnmatch

import pytest

from .spec_loader import SpecLoader
from .test_generator import TestGenerator, resolve_env


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
    group.addoption(
        "--contract-auth",
        action="store",
        default=None,
        help="Auth header, e.g. 'Bearer: token' or 'X-API-Key: secret'",
    )
    group.addoption(
        "--contract-skip-ssl",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification",
    )
    group.addoption(
        "--contract-filter",
        action="store",
        default=None,
        help="Filter endpoints, e.g. 'GET:/users*' or 'POST'",
    )
    group.addoption(
        "--contract-header",
        action="append",
        default=[],
        metavar="KEY:VALUE",
        help="Custom header (repeatable), supports $VAR env expansion",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "contract: mark a test class or function as an API contract test",
    )


def _apply_filter(cases, filter_str):
    """Filter test cases by method/path pattern.

    Examples:
        'GET'           -> all GET endpoints
        'GET:/users*'   -> GET endpoints with path matching /users*
        'POST:/items/*' -> POST /items/* endpoints
    """
    if not filter_str:
        return cases

    if ":" in filter_str:
        method, path_pattern = filter_str.split(":", 1)
        method = method.upper().strip()
        path_pattern = path_pattern.strip()
        return [c for c in cases
                if c.method == method and fnmatch.fnmatch(c.path, path_pattern)]
    else:
        method = filter_str.upper().strip()
        return [c for c in cases if c.method == method]


def pytest_generate_tests(metafunc):
    """Parametrize 'contract_case' fixture for each endpoint in the spec."""
    if "contract_case" not in metafunc.fixturenames:
        return

    spec_path = metafunc.config.getoption("--contract-spec")
    if not spec_path:
        pytest.skip("--contract-spec not provided; cannot generate contract cases")

    if not os.path.exists(spec_path):
        pytest.skip(f"--contract-spec file not found: {spec_path}")

    override_url = metafunc.config.getoption("--contract-base-url")
    auth = metafunc.config.getoption("--contract-auth")
    skip_ssl = metafunc.config.getoption("--contract-skip-ssl")
    filter_str = metafunc.config.getoption("--contract-filter")
    extra_headers = metafunc.config.getoption("--contract-header") or []

    # Parse auth header
    headers = {}
    if auth and ":" in auth:
        key, val = auth.split(":", 1)
        headers[key.strip()] = resolve_env(val.strip())

    # Parse extra headers
    for h in extra_headers:
        if ":" in h:
            key, val = h.split(":", 1)
            headers[key.strip()] = resolve_env(val.strip())

    try:
        loader = SpecLoader(spec_path)
    except Exception as e:
        pytest.skip(f"Failed to load spec: {e}")

    base_url = override_url or loader.get_base_url()
    if not base_url:
        pytest.skip("No base URL found in spec; use --contract-base-url")

    endpoints = loader.get_endpoints()
    if not endpoints:
        pytest.skip("No endpoints found in spec")

    generator = TestGenerator(base_url, endpoints, default_headers=headers)
    cases = generator.generate()

    # Apply SSL setting
    if skip_ssl:
        for c in cases:
            c.verify_ssl = False

    # Apply filter
    if filter_str:
        cases = _apply_filter(cases, filter_str)
        if not cases:
            pytest.skip(f"No endpoints match filter: {filter_str}")

    ids = [f"{c.method} {c.path}" for c in cases]
    metafunc.parametrize("contract_case", cases, ids=ids)