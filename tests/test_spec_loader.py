"""Tests for SpecLoader."""

import pytest
from pytest_api_contract.spec_loader import SpecLoader


def test_load_yaml_spec():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    assert loader.spec["info"]["title"] == "Test API"
    assert loader.spec["openapi"] == "3.0.0"


def test_get_base_url():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    assert loader.get_base_url() == "http://localhost:9999"


def test_get_endpoints_count():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    endpoints = loader.get_endpoints()
    assert len(endpoints) == 3  # GET /users, POST /users, GET /users/{userId}


def test_get_endpoints_method_and_path():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    endpoints = loader.get_endpoints()
    methods = {e["method"] for e in endpoints}
    paths = {e["path"] for e in endpoints}
    assert methods == {"GET", "POST"}
    assert paths == {"/users", "/users/{userId}"}


def test_endpoint_has_operation_id():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    endpoints = loader.get_endpoints()
    get_users = [e for e in endpoints if e["operation_id"] == "getUsers"][0]
    assert get_users["method"] == "GET"
    assert get_users["path"] == "/users"


def test_endpoint_has_parameters():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    endpoints = loader.get_endpoints()
    get_users = [e for e in endpoints if e["operation_id"] == "getUsers"][0]
    assert len(get_users["parameters"]) == 1
    assert get_users["parameters"][0]["name"] == "limit"


def test_endpoint_has_path_params():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    endpoints = loader.get_endpoints()
    get_by_id = [e for e in endpoints if e["operation_id"] == "getUserById"][0]
    path_params = [p for p in get_by_id["parameters"] if p["in"] == "path"]
    assert len(path_params) == 1
    assert path_params[0]["name"] == "userId"


def test_endpoint_has_request_body():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    endpoints = loader.get_endpoints()
    create_user = [e for e in endpoints if e["operation_id"] == "createUser"][0]
    assert create_user["request_body"] is not None
    assert "application/json" in create_user["request_body"]["content"]


def test_unsupported_format_raises():
    with pytest.raises(ValueError, match="Unsupported spec format"):
        SpecLoader("tests/fixtures/test_api.txt")