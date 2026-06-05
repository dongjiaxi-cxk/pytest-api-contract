"""pytest plugin for API contract testing from OpenAPI specs.

Features:
    --contract-spec PATH         Path to OpenAPI 3.x spec
    --contract-base-url URL      Override base URL
    --contract-auth VAL          Auth header (e.g. "Bearer: token")
    --contract-skip-ssl          Disable SSL verification
    --contract-filter VAL        Filter endpoints (method:path pattern)
    --contract-header VAL        Custom header (key:value, repeatable)
    --contract-max-response-ms N  Fail if response exceeds N ms
    --contract-assert-jsonpath   JSONPath assertion (repeatable)
    --contract-snapshot-dir DIR  Snapshot testing directory
"""

import json
import os
import re
import fnmatch
import hashlib

import pytest

from .spec_loader import SpecLoader
from .test_generator import TestGenerator, resolve_env


def pytest_addoption(parser):
    group = parser.getgroup("api-contract")
    group.addoption("--contract-spec", action="store", default=None,
                    help="Path to OpenAPI 3.x spec file (YAML or JSON)")
    group.addoption("--contract-base-url", action="store", default=None,
                    help="Override base URL from spec")
    group.addoption("--contract-auth", action="store", default=None,
                    help="Auth header, e.g. 'Bearer: token'")
    group.addoption("--contract-skip-ssl", action="store_true", default=False,
                    help="Disable SSL certificate verification")
    group.addoption("--contract-filter", action="store", default=None,
                    help="Filter endpoints, e.g. 'GET:/users*'")
    group.addoption("--contract-header", action="append", default=[],
                    metavar="KEY:VALUE", help="Custom header (repeatable)")
    group.addoption("--contract-max-response-ms", action="store", type=int, default=None,
                    help="Fail if response time exceeds N milliseconds")
    group.addoption("--contract-assert-jsonpath", action="append", default=[],
                    metavar="PATH:VALUE", help="Assert JSONPath equals value (repeatable)")
    group.addoption("--contract-snapshot-dir", action="store", default=None,
                    help="Directory for response snapshot testing")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "contract: mark a test class or function as an API contract test",
    )


def _apply_filter(cases, filter_str):
    if not filter_str:
        return cases
    if ":" in filter_str:
        method, path_pattern = filter_str.split(":", 1)
        return [c for c in cases
                if c.method == method.upper().strip() and fnmatch.fnmatch(c.path, path_pattern.strip())]
    else:
        method = filter_str.upper().strip()
        return [c for c in cases if c.method == method]


def _resolve_jsonpath(data, path):
    """Resolve a simple JSONPath expression against data.

    Supports: $, $.foo, $.foo.bar, $.items[0], $.items[0].name, $.items[*].name
    Returns the resolved value or a sentinel if not found.
    """
    _NOT_FOUND = object()

    if not path.startswith("$"):
        return _NOT_FOUND

    parts = re.findall(r"\.(\w+)|\['(\w+)'\]|\[(\d+|\*)\]", path[1:] if path[1:2] == "." else path[2:] if path[1:3] == "[(" else path[1:])
    current = data

    # Parse the path more carefully
    tokens = []
    i = 1
    while i < len(path):
        if path[i] == ".":
            i += 1
            j = i
            while j < len(path) and (path[j].isalnum() or path[j] == "_"):
                j += 1
            tokens.append(("key", path[i:j]))
            i = j
        elif path[i] == "[":
            j = path.index("]", i)
            idx = path[i+1:j]
            if idx == "*":
                tokens.append(("wildcard", "*"))
            else:
                tokens.append(("index", int(idx)))
            i = j + 1
        else:
            i += 1

    for op, val in tokens:
        if current is _NOT_FOUND:
            return _NOT_FOUND
        if op == "key":
            if isinstance(current, dict):
                current = current.get(val, _NOT_FOUND)
            else:
                return _NOT_FOUND
        elif op == "index":
            if isinstance(current, list) and 0 <= val < len(current):
                current = current[val]
            else:
                return _NOT_FOUND
        elif op == "wildcard":
            if isinstance(current, list):
                results = []
                for item in current:
                    remaining = [("key", t[1]) for t in tokens[tokens.index(("wildcard", "*")) + 1:]]
                    v = item
                    for rop, rval in remaining:
                        if isinstance(v, dict):
                            v = v.get(rval, _NOT_FOUND)
                        else:
                            v = _NOT_FOUND
                            break
                    if v is not _NOT_FOUND:
                        results.append(v)
                return results if results else _NOT_FOUND
            return _NOT_FOUND

    return current


def _snapshot_test(response_data, snapshot_path):
    """Compare response against a stored snapshot.

    If snapshot doesn't exist, create it. If it exists, compare.
    Returns (passed, message).
    """
    response_hash = hashlib.sha256(
        json.dumps(response_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    if os.path.exists(snapshot_path):
        with open(snapshot_path, "r", encoding="utf-8") as f:
            stored = json.load(f)
        stored_hash = stored.get("hash", "")
        if response_hash == stored_hash:
            return True, "[PASS] Snapshot matches"
        else:
            return False, "[FAIL] Snapshot mismatch"
    else:
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump({"hash": response_hash, "data": response_data}, f, default=str, indent=2)
        return True, "[PASS] Snapshot created"


def pytest_generate_tests(metafunc):
    if "contract_case" not in metafunc.fixturenames:
        return

    spec_path = metafunc.config.getoption("--contract-spec")
    if not spec_path:
        pytest.skip("--contract-spec not provided; cannot generate contract cases")
    if not os.path.exists(spec_path):
        pytest.skip("--contract-spec file not found: " + spec_path)

    override_url = metafunc.config.getoption("--contract-base-url")
    auth = metafunc.config.getoption("--contract-auth")
    skip_ssl = metafunc.config.getoption("--contract-skip-ssl")
    filter_str = metafunc.config.getoption("--contract-filter")
    extra_headers = metafunc.config.getoption("--contract-header") or []
    max_response_ms = metafunc.config.getoption("--contract-max-response-ms")
    jsonpath_asserts = metafunc.config.getoption("--contract-assert-jsonpath") or []
    snapshot_dir = metafunc.config.getoption("--contract-snapshot-dir")

    headers = {}
    if auth and ":" in auth:
        key, val = auth.split(":", 1)
        headers[key.strip()] = resolve_env(val.strip())
    for h in extra_headers:
        if ":" in h:
            key, val = h.split(":", 1)
            headers[key.strip()] = resolve_env(val.strip())

    try:
        loader = SpecLoader(spec_path)
    except Exception as e:
        pytest.skip("Failed to load spec: " + str(e))

    base_url = override_url or loader.get_base_url()
    if not base_url:
        pytest.skip("No base URL found in spec; use --contract-base-url")

    endpoints = loader.get_endpoints()
    if not endpoints:
        pytest.skip("No endpoints found in spec")

    generator = TestGenerator(base_url, endpoints, default_headers=headers)
    cases = generator.generate()

    if skip_ssl:
        for c in cases:
            c.verify_ssl = False

    if filter_str:
        cases = _apply_filter(cases, filter_str)
        if not cases:
            pytest.skip("No endpoints match filter: " + filter_str)

    # Store extra config on each test case for execute()
    for c in cases:
        c._max_response_ms = max_response_ms
        c._jsonpath_asserts = []
        for ja in jsonpath_asserts:
            if ":" in ja:
                path, expected = ja.split(":", 1)
                c._jsonpath_asserts.append((path.strip(), expected.strip()))
        c._snapshot_dir = snapshot_dir

    ids = [f"{c.method} {c.path}" for c in cases]
    metafunc.parametrize("contract_case", cases, ids=ids)