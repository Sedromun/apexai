"""Declarative base and portable column types.

The GUID/JSON helpers make the same models work on PostgreSQL (production: native
``uuid`` + ``jsonb``) and SQLite (the in-memory test database), so the test suite
needs no external services.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """UUID column: native ``uuid`` on PostgreSQL, ``CHAR(36)`` elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


# ``jsonb`` on PostgreSQL, generic ``json`` everywhere else.
JSONVariant = JSON().with_variant(JSONB, "postgresql")
