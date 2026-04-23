"""Tests for CLI formatters."""

from __future__ import annotations

from click.testing import CliRunner

from papertrail.cli.formatters import print_summary, print_table


def test_print_summary_basic(sample_pipeline_state, capsys):
    state = sample_pipeline_state
    state["classification"] = {"type": "indian_cheque", "confidence": 0.95}
    state["validation_result"] = {"aggregate_confidence": 0.88}
    state["decision_result"] = {
        "action": "approve",
        "enriched_data": {},
        "reasons": [],
    }
    state["extraction_output"] = {
        "elements": [
            {"name": "payee_name", "value": "Test User"},
        ]
    }
    print_summary(state)
    captured = capsys.readouterr()
    assert "approve" in captured.out.lower() or "approve" in captured.out
    assert "Test User" in captured.out


def test_print_table_empty(capsys):
    print_table(["A", "B"], [])
    captured = capsys.readouterr()
    assert "no results" in captured.out
