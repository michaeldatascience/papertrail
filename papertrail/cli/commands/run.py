"""papertrail run — Run a document through the pipeline."""

from __future__ import annotations

import asyncio
import json

import click

from papertrail.cli.formatters import print_json, print_summary


@click.command("run")
@click.argument("file", type=click.Path(exists=True))
@click.option("--playbook", required=True, help="Playbook slug")
@click.option("--version", default=None, help="Playbook version (default: latest)")
@click.option("--force-rerun", is_flag=True, help="Skip duplicate detection")
@click.option("--skip-hitl", is_flag=True, help="Fail if HITL triggered")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["json", "summary", "verbose"]),
    default="summary",
    help="Output format",
)
@click.option("--save", is_flag=True, help="Save output JSON to data/exports/")
def run_cmd(
    file: str,
    playbook: str,
    version: str | None,
    force_rerun: bool,
    skip_hitl: bool,
    output_format: str,
    save: bool,
):
    """Run a document through the processing pipeline."""
    asyncio.run(_run(file, playbook, version, force_rerun, skip_hitl, output_format, save))


async def _run(
    file: str,
    playbook: str,
    version: str | None,
    force_rerun: bool,
    skip_hitl: bool,
    output_format: str,
    save: bool,
):
    from papertrail.orchestration.runner import PipelineRunner

    runner = PipelineRunner()

    click.echo(f"Processing {file} with playbook '{playbook}'...")

    try:
        state = await runner.run(
            file_path=file,
            playbook_slug=playbook,
            playbook_version=version,
            force_rerun=force_rerun,
        )
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)

    if state.get("awaiting_hitl") and skip_hitl:
        click.secho("HITL triggered but --skip-hitl is set. Failing.", fg="red")
        raise SystemExit(1)

    if output_format == "json":
        print_json(dict(state))
    elif output_format == "summary":
        print_summary(dict(state))
    else:
        print_json(dict(state))

    if save:
        from pathlib import Path

        exports_dir = Path("data/exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        out_path = exports_dir / f"{state.get('run_uid', 'unknown')}.json"
        with open(out_path, "w") as f:
            json.dump(dict(state), f, indent=2, default=str)
        click.echo(f"Saved to {out_path}")
