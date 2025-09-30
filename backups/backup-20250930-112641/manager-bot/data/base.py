import logging
from typing import Generator
from typing import Sequence
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import DeclarativeBase, selectinload
from data.tools import session_scope

_logger = logging.getLogger(__name__)


class Model(DeclarativeBase):
	@classmethod
	async def all(cls) -> Sequence['Model']:
		async with session_scope() as session:
			q = select(cls)
			instances = await session.execute(q)
			instances = instances.scalars()
		return instances.unique().all()

	@classmethod
	async def all_with_related(cls) -> Sequence['Model']:
		async with session_scope() as session:
			relationships = cls.__mapper__.relationships
			query_options = [selectinload(relationship) for relationship in relationships.values()]
			q = select(cls).options(*query_options)
			instances = await session.execute(q)
			instances = instances.scalars()
		return instances.unique().all()

	@classmethod
	async def filter_by(cls, **kwargs) -> Sequence['Model']:
		async with session_scope() as session:
			q = select(cls).filter_by(**kwargs)
			instances = await session.execute(q)
			instances = instances.scalars()

		return instances.unique().all()

	@classmethod
	async def filter(cls, *criteria) -> Sequence['Model']:
		async with session_scope() as session:
			q = select(cls).filter(*criteria)
			instances = await session.execute(q)
			instances = instances.scalars()

		return instances.unique().all()

	@classmethod
	async def create(cls, **kwargs) -> 'Model':
		async with session_scope() as session:
			instance = cls(**kwargs)
			session.add(instance)

		return instance

	@classmethod
	async def get(cls, **kwargs) -> 'Model':
		async with session_scope() as session:
			q = select(cls).filter_by(**kwargs)
			instances = await session.execute(q)
			instance = instances.first()

		return instance if instance is None else instance[0]

	@classmethod
	async def get_with_related(cls, **kwargs) -> 'Model':
		async with session_scope() as session:
			relationships = cls.__mapper__.relationships
			query_options = [selectinload(relationship) for relationship in relationships.values()]
			q = select(cls).options(*query_options)
			q = q.filter_by(**kwargs)
			instances = await session.execute(q)
			instance = instances.first()

		return instance if instance is None else instance[0]

	@classmethod
	async def get_or_create(cls, **kwargs) -> tuple['Model', bool]:
		if instance := await cls.get(**kwargs):
			return instance, False
		else:
			instance = await cls.create(**kwargs)
			return instance, True

	async def update(self, **new_values) -> 'Model':
		new_values = self._filter_new_values(new_values)
		async with session_scope() as session:
			unset_values = {
				k: getattr(self, k) for k in self.columns if
				k not in new_values
			}
			q = update(self.__class__).values(**new_values).filter_by(
				**unset_values)
			await session.execute(q)

		for key, value in new_values.items():
			setattr(self, key, value)

		return self

	async def delete(self) -> None:
		async with session_scope() as session:
			await session.delete(self)

	@property
	def columns(self) -> Generator[str, str, None]:
		return (c.key for c in self.__table__.columns)

	def _filter_new_values(self, new_value: dict):
		return {k: v for k, v in new_value.items() if k in self.columns}
