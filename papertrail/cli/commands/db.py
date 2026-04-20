"""papertrail db — Database management commands."""

from __future__ import annotations

import click


@click.group("db")
def db_group():
    """Database management."""
    pass


@db_group.command("migrate")
def db_migrate():
    """Apply pending Alembic migrations."""
    click.echo("Applying migrations...")
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    click.secho("Migrations applied.", fg="green")


@db_group.command("seed")
def db_seed():
    """Seed Playbooks and tools into the DB."""
    import asyncio

    click.echo("Seeding database...")
    asyncio.run(_seed())
    click.secho("Seeding complete.", fg="green")


async def _seed():
    # TODO: Implement seeder that reads playbooks_seed/ and inserts into DB
    click.echo("  (Seeder not yet implemented — will import from playbooks_seed/)")


@db_group.command("reset")
@click.confirmation_option(prompt="This will drop ALL tables. Are you sure?")
def db_reset():
    """Drop all tables and re-create (dev only)."""
    click.echo("Resetting database...")
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    click.secho("Database reset complete.", fg="green")
