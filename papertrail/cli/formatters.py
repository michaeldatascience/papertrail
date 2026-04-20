"""Pretty-print helpers for CLI output."""

from __future__ import annotations

import json

import click


def print_summary(state: dict) -> None:
    """Print a compact one-screen run summary."""
    run_uid = state.get("run_uid", "unknown")
    decision_result = state.get("decision_result", {})
    classification = state.get("classification", {})
    pass_d = state.get("pass_d_output", {})
    warnings = state.get("warnings", [])

    decision = decision_result.get("action", "unknown") if decision_result else "unknown"
    confidence = pass_d.get("aggregate_confidence", 0.0) if pass_d else 0.0
    doc_type = classification.get("type", "unknown") if classification else "unknown"

    click.echo()
    click.secho(f"Run: {run_uid}", fg="cyan", bold=True)
    click.echo(f"Document Type: {doc_type}")

    status_color = {
        "approve": "green", "flag": "yellow", "reject": "red", "escalate": "magenta"
    }.get(decision, "white")
    click.secho(f"Decision: {decision}", fg=status_color, bold=True)
    click.echo(f"Confidence: {confidence:.2f}")
    click.echo(f"Warnings: {len(warnings)}")

    # Extracted elements
    pass_c = state.get("pass_c_output", {})
    elements = pass_c.get("elements", []) if pass_c else []
    if elements:
        click.echo()
        click.secho("Extracted:", bold=True)
        for elem in elements:
            name = elem.get("name", "?")
            value = elem.get("value", "null")
            click.echo(f"  {name}: {value}")

    # Enriched data
    enriched = decision_result.get("enriched_data", {}) if decision_result else {}
    if enriched:
        click.echo()
        click.secho("Enriched:", bold=True)
        for key, val in enriched.items():
            click.echo(f"  {key}: {val}")

    # Reasons
    reasons = decision_result.get("reasons", []) if decision_result else []
    if reasons:
        click.echo()
        click.secho("Reasons:", bold=True)
        for reason in reasons:
            click.echo(f"  - {reason}")

    # Error
    error = state.get("error")
    if error:
        click.echo()
        click.secho(f"Error: {error}", fg="red")

    click.echo()


def print_json(data: dict) -> None:
    """Print formatted JSON."""
    click.echo(json.dumps(data, indent=2, default=str))


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple aligned table."""
    if not rows:
        click.echo("(no results)")
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    click.secho(header_line, bold=True)
    for row in rows:
        line = "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
        click.echo(line)
