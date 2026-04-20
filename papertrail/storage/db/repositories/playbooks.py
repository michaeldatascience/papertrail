"""Playbook repository — CRUD for playbooks and configs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from papertrail.storage.db.models import PlaybookConfigModel, PlaybookModel


class PlaybookRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_slug(
        self, slug: str, version: str | None = None
    ) -> PlaybookModel | None:
        query = (
            select(PlaybookModel)
            .options(selectinload(PlaybookModel.configs))
            .where(PlaybookModel.slug == slug, PlaybookModel.is_active.is_(True))
        )
        if version:
            query = query.where(PlaybookModel.version == version)
        else:
            query = query.order_by(PlaybookModel.created_at.desc()).limit(1)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, playbook_id: UUID) -> PlaybookModel | None:
        result = await self._session.execute(
            select(PlaybookModel)
            .options(selectinload(PlaybookModel.configs))
            .where(PlaybookModel.id == playbook_id)
        )
        return result.scalar_one_or_none()

    async def list_playbooks(self, active_only: bool = True) -> list[PlaybookModel]:
        query = select(PlaybookModel).order_by(PlaybookModel.slug, PlaybookModel.version)
        if active_only:
            query = query.where(PlaybookModel.is_active.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def upsert(self, playbook: PlaybookModel) -> PlaybookModel:
        self._session.add(playbook)
        await self._session.flush()
        return playbook

    async def upsert_config(self, config: PlaybookConfigModel) -> PlaybookConfigModel:
        self._session.add(config)
        await self._session.flush()
        return config
