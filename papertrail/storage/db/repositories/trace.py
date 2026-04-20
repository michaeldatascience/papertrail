"""Trace event repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from papertrail.storage.db.models import TraceEventModel


class TraceRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def emit(self, **kwargs) -> TraceEventModel:
        event = TraceEventModel(**kwargs)
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_for_run(self, run_id: UUID) -> list[TraceEventModel]:
        result = await self._session.execute(
            select(TraceEventModel)
            .where(TraceEventModel.run_id == run_id)
            .order_by(TraceEventModel.ts.asc())
        )
        return list(result.scalars().all())
