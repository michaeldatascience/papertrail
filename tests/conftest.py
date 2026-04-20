"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_pipeline_state() -> dict:
    """A minimal pipeline state for testing."""
    return {
        "run_id": "test-run-001",
        "run_uid": "run_20260420_120000_indian_cheque_abc123",
        "playbook_id": "test-playbook-id",
        "playbook": {
            "meta": {"document_type": "indian_cheque"},
            "classify": {"hitl_threshold": 0.6},
            "validate": {"correction": {"max_attempts": 3}},
        },
        "input_file_uri": "/tmp/test_cheque.jpg",
        "input_file_hash": "abc123def456",
        "input_file_mime": "image/jpeg",
        "preupload_result": None,
        "classification": None,
        "pass_a_output": None,
        "pass_b_output": None,
        "pass_c_output": None,
        "pass_d_output": None,
        "correction_attempts": 0,
        "correction_history": [],
        "decision_result": None,
        "awaiting_hitl": False,
        "hitl_checkpoint_type": None,
        "hitl_context": None,
        "confidence_budget": 1.0,
        "warnings": [],
        "error": None,
        "failed_stage": None,
    }
