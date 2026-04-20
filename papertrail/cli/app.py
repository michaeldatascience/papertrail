"""PaperTrail CLI — Click entry point."""

from __future__ import annotations

import click

from papertrail.cli.commands.run import run_cmd
from papertrail.cli.commands.playbook import playbook_group
from papertrail.cli.commands.runs import runs_group
from papertrail.cli.commands.hitl import hitl_group
from papertrail.cli.commands.db import db_group
from papertrail.cli.commands.eval import eval_group


@click.group()
@click.version_option(version="1.0.0", prog_name="papertrail")
def cli():
    """PaperTrail — Agentic document processing pipeline."""
    pass


cli.add_command(run_cmd, "run")
cli.add_command(playbook_group, "playbook")
cli.add_command(runs_group, "runs")
cli.add_command(hitl_group, "hitl")
cli.add_command(db_group, "db")
cli.add_command(eval_group, "eval")


if __name__ == "__main__":
    cli()
