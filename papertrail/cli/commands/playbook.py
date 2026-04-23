"""papertrail playbook — Playbook management commands."""

from __future__ import annotations

import click

from papertrail.cli.formatters import print_table


@click.group("playbook")
def playbook_group():
    """Manage Playbooks."""
    pass


@playbook_group.command("list")
def playbook_list():
    """List available Playbooks."""
    # TODO: Query database for playbooks
    headers = ["SLUG", "VERSION", "NAME", "ACTIVE"]
    rows = [
        ["indian_cheque", "1.0", "Indian Cheque", "yes"],
        ["indian_bank_statement", "1.0", "Indian Bank Statement", "yes"],
        ["indian_salary_slip", "1.0", "Indian Salary Slip", "yes"],
        ["indian_itr_form", "1.0", "Indian ITR Form", "yes"],
    ]
    print_table(headers, rows)


@playbook_group.command("show")
@click.argument("slug")
@click.option("--version", default=None, help="Playbook version")
def playbook_show(slug: str, version: str | None):
    """Show a Playbook's merged config."""
    # TODO: Load and merge playbook from database
    click.echo(f"Showing merged config for playbook '{slug}' (version: {version or 'latest'})")
    click.echo("(Not yet implemented — will show merged JSON after DB integration)")


@playbook_group.command("validate")
@click.argument("slug")
def playbook_validate(slug: str):
    """Validate a Playbook's config."""
    # TODO: Run playbook validator
    click.secho(f"Playbook '{slug}' validation: OK", fg="green")


@playbook_group.command("import")
@click.argument("folder", type=click.Path(exists=True))
def playbook_import(folder: str):
    """Import a Playbook folder into the DB."""
    # TODO: Import playbook from folder
    click.echo(f"Importing playbook from '{folder}'...")
    click.echo("(Not yet implemented)")


@playbook_group.command("export")
@click.argument("slug")
@click.option("--output", "-o", default=".", help="Output directory")
def playbook_export(slug: str, output: str):
    """Export a DB Playbook to a folder."""
    # TODO: Export playbook to folder
    click.echo(f"Exporting playbook '{slug}' to '{output}'...")
    click.echo("(Not yet implemented)")
