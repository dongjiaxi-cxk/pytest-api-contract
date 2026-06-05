"""Tests for TestGenerator and TestCase."""

import pytest
from pytest_api_contract.spec_loader import SpecLoader
from pytest_api_contract.test_generator import TestGenerator, TestCase


@pytest.fixture
def endpoints():
    loader = SpecLoader("tests/fixtures/test_api.yaml")
    return loader.get_endpoints()


@pytest.fixture
def generator(endpoints):
    return TestGenerator("http://localhost:9999", endpoints)


@pytest.fixture
def cases(generator):
    return generator.generate()


class TestTestGenerator:
    def test_generates_correct_count(self, cases):
        assert len(cases) == 3

    def test_generates_test_case_type(self, cases):
        for case in cases:
            assert isinstance(case, TestCase)

    def test_query_params_generated(self, cases):
        get_users = [c for c in cases if c.name == "getUsers"][0]
        assert "limit" in get_users.params
        assert get_users.params["limit"] == 1  # integer default

    def test_path_params_generated(self, cases):
        get_by_id = [c for c in cases if c.name == "getUserById"][0]
        assert "userId" in get_by_id.path_params
        assert get_by_id.path_params["userId"] == 1

    def test_request_body_generated(self, cases):
        create_user = [c for c in cases if c.name == "createUser"][0]
        assert create_user.body is not None
        assert "name" in create_user.body

    def test_expected_status(self, cases):
        get_users = [c for c in cases if c.name == "getUsers"][0]
        assert get_users.expected_status == 200

    def test_expected_status_201(self, cases):
        create_user = [c for c in cases if c.name == "createUser"][0]
        assert create_user.expected_status == 201

    def test_response_schema_present(self, cases):
        get_users = [c for c in cases if c.name == "getUsers"][0]
        assert get_users.response_schema is not None
        assert get_users.response_schema["type"] == "array"

    def test_no_body_for_get(self, cases):
        get_users = [c for c in cases if c.name == "getUsers"][0]
        assert get_users.body is None

    def test_base_url_applied(self, cases):
        for case in cases:
            assert case.base_url == "http://localhost:9999"


class TestCaseTest:
    def test_execute_connection_error(self):
        case = TestCase(
            name="test",
            method="GET",
            path="/nonexistent",
            base_url="http://localhost:19999",
        )
        result = case.execute(timeout=1)
        assert not result["passed"]
        assert result["error"] is not None
        assert any("[FAIL]" in m for m in result["messages"])