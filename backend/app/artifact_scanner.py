"""Workspace artifact scanner.

After each Claude turn, scan <workspace>/artifacts/*.chart.json for files
written during that turn. Validate the Plotly shape; skip (warn) malformed ones.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import structlog

_log = structlog.get_logger(__name__)


@dataclass
class ChartArtifact:
    artifact_id: str
    title: str
    file_path: Path
    payload: dict = field(default_factory=dict)


def scan_for_charts(workspace_path: Path, since_ts: float) -> list[ChartArtifact]:
    """Return ChartArtifacts for any *.chart.json written after since_ts.

    Args:
        workspace_path: Root of the session workspace.
        since_ts: Unix timestamp (float, from time.time()) captured at turn start.
                  Files with mtime <= since_ts are ignored.

    Returns:
        List of validated ChartArtifact instances. Malformed or old files are skipped.
    """
    artifacts_dir = workspace_path / "artifacts"
    if not artifacts_dir.is_dir():
        return []

    results: list[ChartArtifact] = []
    for chart_file in artifacts_dir.glob("*.chart.json"):
        try:
            mtime = chart_file.stat().st_mtime
        except OSError:
            continue  # file disappeared between glob and stat

        if mtime <= since_ts:
            continue  # written before this turn started

        try:
            raw = chart_file.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning(
                "artifact_scanner.malformed_json",
                file=str(chart_file),
                error=str(exc),
            )
            continue

        if not isinstance(payload, dict):
            _log.warning("artifact_scanner.not_a_dict", file=str(chart_file))
            continue

        if "data" not in payload or not isinstance(payload.get("data"), list):
            _log.warning(
                "artifact_scanner.missing_data_key",
                file=str(chart_file),
            )
            continue

        # Optional keys — tolerate absence or wrong type with defaults.
        raw_title = payload.get("title")
        # chart_file.name is e.g. "equity.chart.json" — strip both suffixes
        # to get the logical name "equity".
        name_stem = chart_file.stem  # "equity.chart"
        if name_stem.endswith(".chart"):
            name_stem = name_stem[: -len(".chart")]
        title = str(raw_title) if raw_title and isinstance(raw_title, str) else name_stem

        layout = payload.get("layout")
        if not isinstance(layout, dict):
            layout = {}

        validated_payload: dict = {
            "title": title,
            "data": payload["data"],
            "layout": layout,
        }

        artifact_id = uuid.uuid4().hex
        results.append(
            ChartArtifact(
                artifact_id=artifact_id,
                title=title,
                file_path=chart_file,
                payload=validated_payload,
            )
        )

    return results
