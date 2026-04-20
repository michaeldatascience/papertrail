"""HITL event repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from papertrail.storage.db.models import RunHITLEventModel


class HITLRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, **kwargs) -> RunHITLEventModel:
        event = RunHITLEventModel(**kwargs)
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_pending(self) -> list[RunHITLEventModel]:
        result = await self._session.execute(
            select(RunHITLEventModel)
            .where(RunHITLEventModel.status == "awaiting")
            .order_by(RunHITLEventModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def resolve(
        self, event_id: UUID, resolution: dict, resolved_by: str | None = None
    ) -> None:
        await self._session.execute(
            update(RunHITLEventModel)
            .where(RunHITLEventModel.id == event_id)
            .values(
                status="resolved",
                resolution=resolution,
                resolved_by=resolved_by,
                resolved_at=datetime.utcnow(),
            )
        )
