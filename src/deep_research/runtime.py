from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

@dataclass(frozen=True)
class Deps:
    sessionmaker: async_sessionmaker[AsyncSession]
