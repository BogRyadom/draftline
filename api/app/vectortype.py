"""Minimal pgvector column type for SQLAlchemy.

Avoids the `pgvector` Python package (and its numpy dependency): binds a list of
floats as the pgvector text form and casts it to `vector` in SQL, exposes the
`<=>` cosine-distance operator, and parses results back to a list. The spec
explicitly allows raw SQL for vector search — this is that, wrapped in a type.
"""

from __future__ import annotations

from sqlalchemy import Float, cast, literal
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim

    def get_col_spec(self, **kw) -> str:
        return "vector" if self.dim is None else f"vector({self.dim})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            return "[" + ",".join(repr(float(x)) for x in value) + "]"

        return process

    def bind_expression(self, bindvalue):
        # Ensure the bound text is cast to `vector(dim)` in the SQL.
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return list(value)
            s = str(value).strip().lstrip("[").rstrip("]")
            return [float(x) for x in s.split(",")] if s else []

        return process

    class Comparator(UserDefinedType.Comparator):
        def cosine_distance(self, other):
            return self.op("<=>", return_type=Float)(literal(other, self.type))

    comparator_factory = Comparator
