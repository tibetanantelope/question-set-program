"""Apply explicitly selected numbered SQL migrations."""

import argparse
import asyncio
import re
from pathlib import Path

from sqlalchemy import text

from backend.model import engine

ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT / "database"
ALLOWED_NAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")


def split_statements(sql: str) -> list[str]:
    sql = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]


async def apply(files: list[str]) -> None:
    paths: list[Path] = []
    for name in files:
        if not ALLOWED_NAME.fullmatch(name):
            raise ValueError(f"非法迁移文件名：{name}")
        path = (DATABASE_DIR / name).resolve()
        if path.parent != DATABASE_DIR.resolve() or not path.is_file():
            raise FileNotFoundError(name)
        paths.append(path)

    async with engine.begin() as connection:
        await connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version VARCHAR(20) PRIMARY KEY,
                description VARCHAR(200) NOT NULL,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        existing = set(
            (
                await connection.execute(
                    text("SELECT version FROM schema_version")
                )
            ).scalars()
        )
        for path in paths:
            version = path.name[:3]
            if version in existing:
                print(f"SKIP {path.name}: version already applied")
                continue
            for statement in split_statements(path.read_text(encoding="utf-8")):
                await connection.exec_driver_sql(statement)
            print(f"APPLIED {path.name}")

    await engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    await apply(args.files)


if __name__ == "__main__":
    asyncio.run(main())
