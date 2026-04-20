"""Tests for pipeline routing logic."""

from __future__ import annotations

from papertrail.orchestration.routing import route_after_classify, route_after_validation


def test_route_after_classify_proceed(sample_pipeline_state):
    state = sample_pipeline_state
    state["classification"] = {"type": "indian_cheque", "confidence": 0.95}
    assert route_after_classify(state) == "proceed"


def test_route_after_classify_hitl(sample_pipeline_state):
    state = sample_pipeline_state
    state["classification"] = {"type": "indian_cheque", "confidence": 0.4}
    assert route_after_classify(state) == "hitl"


def test_route_after_classify_no_classification(sample_pipeline_state):
    state = sample_pipeline_state
    state["classification"] = None
    assert route_after_classify(state) == "error"


def test_route_after_validation_proceed(sample_pipeline_state):
    state = sample_pipeline_state
    state["pass_d_output"] = {"passed": True}
    assert route_after_validation(state) == "proceed"


def test_route_after_validation_retry(sample_pipeline_state):
    state = sample_pipeline_state
    state["pass_d_output"] = {"passed": False}
    state["correction_attempts"] = 0
    assert route_after_validation(state) == "retry"


def test_route_after_validation_exhausted(sample_pipeline_state):
    state = sample_pipeline_state
    state["pass_d_output"] = {"passed": False}
    state["correction_attempts"] = 3
    assert route_after_validation(state) == "exhausted"


def test_route_after_validation_no_result(sample_pipeline_state):
    state = sample_pipeline_state
    state["pass_d_output"] = None
    assert route_after_validation(state) == "error"
