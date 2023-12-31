from __future__ import annotations

import itertools
from typing import List, cast

import numpy as np
import numpy.typing as npt
import sqlalchemy
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select

from revolve2.core.database import IncompatibleError

from .._serializer import Serializer


class Ndarray1xnSerializer(Serializer[npt.NDArray[np.float_]]):
    @classmethod
    async def create_tables(cls, session: AsyncSession) -> None:
        await (await session.connection()).run_sync(DbBase.metadata.create_all)

    @classmethod
    def identifying_table(cls) -> str:
        return DbNdarray1xn.__tablename__

    @classmethod
    async def to_database(
        cls, session: AsyncSession, objects: List[npt.NDArray[np.float_]]
    ) -> List[int]:
        dblists = [DbNdarray1xn() for _ in objects]
        session.add_all(dblists)
        await session.flush()
        ids = [
            dbfitness.id for dbfitness in dblists if dbfitness.id is not None
        ]  # cannot be none because not nullable but adding check for mypy
        assert len(ids) == len(objects)  # just to be sure because of check above

        items = [
            DbNdarray1xnItem(nparray1xn_id=id, array_index=i, value=v)
            for id, values in zip(ids, objects)
            for i, v in enumerate(values)
        ]

        session.add_all(items)

        return ids

    @classmethod
    async def from_database(
        cls, session: AsyncSession, ids: List[int]
    ) -> List[npt.NDArray[np.float_]]:
        items = (
            (
                await session.execute(
                    select(DbNdarray1xnItem)
                    .filter(DbNdarray1xnItem.nparray1xn_id.in_(ids))
                    .order_by(DbNdarray1xnItem.array_index)
                )
            )
            .scalars()
            .all()
        )

        arrays: List[npt.NDArray[np.float_]] = [
            np.array([item.value for item in group])
            for _, group in itertools.groupby(
                items, key=lambda item: cast(int, item.nparray1xn_id)
            )
        ]  # cast to int to silence mypy

        if len(arrays) != len(ids):
            IncompatibleError()

        return arrays


DbBase = declarative_base()


class DbNdarray1xn(DbBase):
    __tablename__ = "nparray1xn"

    id = sqlalchemy.Column(
        sqlalchemy.Integer, nullable=False, primary_key=True, autoincrement=True
    )


class DbNdarray1xnItem(DbBase):
    __tablename__ = "nparray1xn_item"

    nparray1xn_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(DbNdarray1xn.id),
        nullable=False,
        primary_key=True,
    )
    array_index = sqlalchemy.Column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
    )
    value = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
