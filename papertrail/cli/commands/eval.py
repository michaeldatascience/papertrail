"""papertrail eval — Evaluation commands."""

from __future__ import annotations

import click


@click.group("eval")
def eval_group():
    """Evaluation and benchmarking."""
    pass


@eval_group.command("run")
@click.option("--dataset", default=None, help="Dataset name (e.g., cheques)")
def eval_run(dataset: str | None):
    """Run the evaluation dataset."""
    # TODO: Implement evaluation runner
    click.echo(f"Running evaluation dataset: {dataset or 'all'}")
    click.echo("(Not yet implemented)")
