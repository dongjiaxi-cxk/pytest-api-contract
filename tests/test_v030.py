"""Tests for v0.3.0: max-response-ms, JSONPath assertions, snapshot testing."""

import json, os, subprocess, sys, tempfile
from pathlib import Path
from pytest_api_contract.plugin import _resolve_jsonpath, _snapshot_test


class TestJSONPath:
    def test_root(self):
        assert _resolve_jsonpath({"a": 1}, "$") == {"a": 1}

    def test_key(self):
        assert _resolve_jsonpath({"name": "test"}, "$.name") == "test"

    def test_nested_key(self):
        assert _resolve_jsonpath({"user": {"name": "alice"}}, "$.user.name") == "alice"

    def test_array_index(self):
        assert _resolve_jsonpath(["a", "b", "c"], "$[1]") == "b"

    def test_nested_array(self):
        data = {"items": [{"id": 1}, {"id": 2}]}
        assert _resolve_jsonpath(data, "$.items[0].id") == 1

    def test_not_found_key(self):
        assert _resolve_jsonpath({"a": 1}, "$.b") is not None  # _NOT_FOUND sentinel

    def test_wildcard(self):
        data = {"items": [{"name": "a"}, {"name": "b"}]}
        result = _resolve_jsonpath(data, "$.items[*].name")
        assert result == ["a", "b"]


class TestSnapshot:
    def test_create_and_match(self):
        tmp = tempfile.mkdtemp()
        snap_path = os.path.join(tmp, "test_snap.json")
        data = {"status": "ok", "count": 42}

        # First call: creates snapshot
        ok, msg = _snapshot_test(data, snap_path)
        assert ok
        assert "created" in msg.lower()

        # Second call: matches
        ok2, msg2 = _snapshot_test(data, snap_path)
        assert ok2
        assert "matches" in msg2.lower()

        # Mismatch
        ok3, msg3 = _snapshot_test({"status": "changed"}, snap_path)
        assert not ok3
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


class TestMaxResponseTimeCLI:
    def test_max_response_time_option_in_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            capture_output=True, text=True,
        )
        assert "--contract-max-response-ms" in result.stdout


class TestJSONPathCLI:
    def test_jsonpath_option_in_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            capture_output=True, text=True,
        )
        assert "--contract-assert-jsonpath" in result.stdout


class TestSnapshotCLI:
    def test_snapshot_option_in_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            capture_output=True, text=True,
        )
        assert "--contract-snapshot-dir" in result.stdout