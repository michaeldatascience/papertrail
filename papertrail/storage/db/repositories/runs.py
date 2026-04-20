"""Run repository — CRUD operations for runs and run_passes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from papertrail.storage.db.models import RunModel, RunPassModel


class RunRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, **kwargs) -> RunModel:
        run = RunModel(**kwargs)
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: UUID) -> RunModel | None:
        return await self._session.get(RunModel, run_id)

    async def get_by_uid(self, run_uid: str) -> RunModel | None:
        result = await self._session.execute(
            select(RunModel).where(RunModel.run_uid == run_uid)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str, within_days: int = 7) -> RunModel | None:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=within_days)
        result = await self._session.execute(
            select(RunModel)
            .where(
                RunModel.input_file_hash == file_hash,
                RunModel.status == "completed",
                RunModel.created_at > cutoff,
            )
            .order_by(RunModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_status(self, run_id: UUID, status: str, **kwargs) -> None:
        await self._session.execute(
            update(RunModel)
            .where(RunModel.id == run_id)
            .values(status=status, **kwargs)
        )

    async def list_runs(
        self,
        playbook_slug: str | None = None,
        status: str | None = None,
        decision: str | None = None,
        limit: int = 20,
    ) -> list[RunModel]:
        query = select(RunModel).order_by(RunModel.created_at.desc()).limit(limit)
        if playbook_slug:
            query = query.where(RunModel.playbook_slug == playbook_slug)
        if status:
            query = query.where(RunModel.status == status)
        if decision:
            query = query.where(RunModel.decision == decision)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_pass(self, **kwargs) -> RunPassModel:
        run_pass = RunPassModel(**kwargs)
        self._session.add(run_pass)
        await self._session.flush()
        return run_pass
