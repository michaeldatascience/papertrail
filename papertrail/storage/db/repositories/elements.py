"""Element and correction repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from papertrail.storage.db.models import RunCorrectionModel, RunElementModel


class ElementRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, **kwargs) -> RunElementModel:
        element = RunElementModel(**kwargs)
        self._session.add(element)
        await self._session.flush()
        return element

    async def get_final_elements(self, run_id: UUID) -> list[RunElementModel]:
        result = await self._session.execute(
            select(RunElementModel)
            .where(RunElementModel.run_id == run_id, RunElementModel.is_final.is_(True))
            .order_by(RunElementModel.element_name)
        )
        return list(result.scalars().all())

    async def create_correction(self, **kwargs) -> RunCorrectionModel:
        correction = RunCorrectionModel(**kwargs)
        self._session.add(correction)
        await self._session.flush()
        return correction
