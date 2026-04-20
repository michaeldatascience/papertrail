"""papertrail hitl — Human-in-the-loop management."""

from __future__ import annotations

import click

from papertrail.cli.formatters import print_table


@click.group("hitl")
def hitl_group():
    """Manage HITL checkpoints."""
    pass


@hitl_group.command("list")
def hitl_list():
    """Show pending HITL checkpoints."""
    # TODO: Query run_hitl_events where status = 'awaiting'
    headers = ["RUN_UID", "CHECKPOINT", "WAITING"]
    rows = []  # Will be populated from DB
    print_table(headers, rows)


@hitl_group.command("resolve")
@click.argument("run_uid")
def hitl_resolve(run_uid: str):
    """Resolve a checkpoint and resume the run."""
    # TODO: Interactive resolution based on checkpoint type
    click.echo(f"Resolving checkpoint for run '{run_uid}'...")
    click.echo("(Not yet implemented — will be interactive after DB integration)")
