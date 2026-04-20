"""papertrail runs — Query and inspect runs."""

from __future__ import annotations

import click

from papertrail.cli.formatters import print_table


@click.group("runs")
def runs_group():
    """Query and inspect pipeline runs."""
    pass


@runs_group.command("list")
@click.option("--playbook", default=None, help="Filter by playbook slug")
@click.option("--decision", default=None, help="Filter by decision")
@click.option("--status", default=None, help="Filter by status")
@click.option("--limit", default=20, help="Max results")
def runs_list(playbook: str | None, decision: str | None, status: str | None, limit: int):
    """List recent runs."""
    # TODO: Query database
    headers = ["RUN_UID", "PLAYBOOK", "STATUS", "DECISION", "CONF", "CREATED"]
    rows = []  # Will be populated from DB
    print_table(headers, rows)


@runs_group.command("show")
@click.argument("run_uid")
def runs_show(run_uid: str):
    """Show run details and final output."""
    # TODO: Query database for run details
    click.echo(f"Run details for '{run_uid}'")
    click.echo("(Not yet implemented — will show full run details after DB integration)")


@runs_group.command("trace")
@click.argument("run_uid")
def runs_trace(run_uid: str):
    """Show the full trace log for a run."""
    # TODO: Query trace_events table
    click.echo(f"Trace log for '{run_uid}'")
    click.echo("(Not yet implemented — will show trace events after DB integration)")
