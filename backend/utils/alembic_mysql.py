"""MySQL conditional DDL uses catalog checks, since it lacks MariaDB's syntax."""

from typing import Any

from alembic.ddl.mysql import MySQLImpl
from sqlalchemy import inspect


class PortableMySQLImpl(MySQLImpl):
    __dialect__ = "mysql"

    def _exists(self, table: str, name: str, kind: str, schema=None) -> bool:
        if self.as_sql:
            raise RuntimeError("Conditional MySQL DDL requires an online catalog")
        inspector = inspect(self.connection)
        members = (
            inspector.get_indexes(table, schema=schema)
            if kind == "index"
            else inspector.get_columns(table, schema=schema)
        )
        return any(member["name"] == name for member in members)

    def create_index(self, index, **kw: Any) -> None:
        if kw.pop("if_not_exists", False) and self._exists(
            index.table.name, index.name, "index", index.table.schema
        ):
            return
        super().create_index(index, **kw)

    def drop_index(self, index, **kw: Any) -> None:
        if kw.pop("if_exists", False) and not self._exists(
            index.table.name, index.name, "index", index.table.schema
        ):
            return
        super().drop_index(index, **kw)

    def add_column(self, table_name, column, *, schema=None, **kw: Any) -> None:
        if kw.pop("if_not_exists", False) and self._exists(
            table_name, column.name, "column", schema
        ):
            return
        super().add_column(table_name, column, schema=schema, **kw)

    def drop_column(self, table_name, column, *, schema=None, **kw: Any) -> None:
        if kw.pop("if_exists", False) and not self._exists(
            table_name, column.name, "column", schema
        ):
            return
        super().drop_column(table_name, column, schema=schema, **kw)
