"""Tests for artifact_scanner.py."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from app.artifact_scanner import ChartArtifact, scan_for_charts


def _write_chart(directory: Path, name: str, payload: dict) -> Path:
    """Helper: write a *.chart.json file into directory/artifacts/."""
    artifacts_dir = directory / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"{name}.chart.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Happy-path: valid chart returned
# ---------------------------------------------------------------------------

def test_valid_chart_returned(tmp_path: Path):
    since = time.time() - 1  # one second ago; file will be newer
    payload = {
        "title": "Equity Curve",
        "data": [{"type": "scatter", "x": [1, 2], "y": [10, 20]}],
        "layout": {"xaxis": {"title": "Day"}},
    }
    _write_chart(tmp_path, "equity", payload)

    results = scan_for_charts(tmp_path, since)
    assert len(results) == 1
    art = results[0]
    assert isinstance(art, ChartArtifact)
    assert art.title == "Equity Curve"
    assert art.payload["data"] == payload["data"]
    assert art.payload["layout"] == payload["layout"]
    assert len(art.artifact_id) == 32  # uuid4 hex
    assert art.file_path.name == "equity.chart.json"


def test_artifact_id_is_unique_per_call(tmp_path: Path):
    since = time.time() - 1
    payload = {"data": [{}], "layout": {}}
    _write_chart(tmp_path, "chart_a", payload)
    _write_chart(tmp_path, "chart_b", payload)

    results = scan_for_charts(tmp_path, since)
    ids = [r.artifact_id for r in results]
    assert len(set(ids)) == len(ids), "each scan call should produce unique artifact_ids"


# ---------------------------------------------------------------------------
# Title fallback to filename stem when title key absent
# ---------------------------------------------------------------------------

def test_title_falls_back_to_stem(tmp_path: Path):
    since = time.time() - 1
    payload = {"data": [{"x": [0], "y": [0]}]}  # no "title" key
    _write_chart(tmp_path, "my_chart", payload)

    results = scan_for_charts(tmp_path, since)
    assert len(results) == 1
    assert results[0].title == "my_chart"


# ---------------------------------------------------------------------------
# Old file (mtime <= since_ts) must be skipped
# ---------------------------------------------------------------------------

def test_old_file_skipped(tmp_path: Path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    chart_file = artifacts_dir / "old.chart.json"
    chart_file.write_text(
        json.dumps({"title": "Old", "data": [{}], "layout": {}}),
        encoding="utf-8",
    )
    # Backdate the file to the past.
    old_ts = time.time() - 100
    os.utime(chart_file, (old_ts, old_ts))

    # since_ts is now (after the file was backdated)
    since = time.time() - 50  # file mtime < since_ts
    results = scan_for_charts(tmp_path, since)
    assert results == []


# ---------------------------------------------------------------------------
# Malformed files: skipped, not raised
# ---------------------------------------------------------------------------

def test_malformed_json_skipped(tmp_path: Path):
    since = time.time() - 1
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    bad = artifacts_dir / "bad.chart.json"
    bad.write_text("{this is not json", encoding="utf-8")

    # Valid file alongside it
    payload = {"data": [{}], "layout": {}}
    _write_chart(tmp_path, "good", payload)

    results = scan_for_charts(tmp_path, since)
    assert len(results) == 1
    assert results[0].title == "good"


def test_missing_data_key_skipped(tmp_path: Path):
    since = time.time() - 1
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    no_data = artifacts_dir / "nodata.chart.json"
    no_data.write_text(json.dumps({"title": "Oops", "layout": {}}), encoding="utf-8")

    results = scan_for_charts(tmp_path, since)
    assert results == []


def test_data_not_a_list_skipped(tmp_path: Path):
    since = time.time() - 1
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    bad_data = artifacts_dir / "bad_data.chart.json"
    bad_data.write_text(
        json.dumps({"title": "Bad", "data": "not-a-list", "layout": {}}),
        encoding="utf-8",
    )

    results = scan_for_charts(tmp_path, since)
    assert results == []


def test_not_a_dict_skipped(tmp_path: Path):
    since = time.time() - 1
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    array_file = artifacts_dir / "array.chart.json"
    array_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    results = scan_for_charts(tmp_path, since)
    assert results == []


# ---------------------------------------------------------------------------
# Missing artifacts dir returns empty list (no crash)
# ---------------------------------------------------------------------------

def test_no_artifacts_dir_returns_empty(tmp_path: Path):
    results = scan_for_charts(tmp_path, time.time())
    assert results == []


# ---------------------------------------------------------------------------
# Layout absent defaults to {} (tolerant parsing)
# ---------------------------------------------------------------------------

def test_layout_defaults_to_empty_dict(tmp_path: Path):
    since = time.time() - 1
    payload = {"title": "No Layout", "data": [{"x": [1], "y": [2]}]}
    _write_chart(tmp_path, "nolayout", payload)

    results = scan_for_charts(tmp_path, since)
    assert len(results) == 1
    assert results[0].payload["layout"] == {}


# ---------------------------------------------------------------------------
# Malformed-input fuzz (required by spec — basic parametric coverage)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_payload", [
    None,
    42,
    "a string",
    [],
    {},  # dict but no "data" key
    {"data": None},  # data is not a list
    {"data": {}, "layout": {}},  # data is a dict, not list
])
def test_malformed_payloads_skipped(tmp_path: Path, bad_payload):
    since = time.time() - 1
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    p = artifacts_dir / "fuzz.chart.json"
    p.write_text(json.dumps(bad_payload), encoding="utf-8")

    # Must not raise; must return empty list.
    results = scan_for_charts(tmp_path, since)
    assert isinstance(results, list)
    assert len(results) == 0
