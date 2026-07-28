"""联调前环境与数据库版本检查（只读，不执行迁移）。"""

import argparse
import asyncio
import os

from backend.env import load_backend_env

EXPECTED_SCHEMA_VERSION = "010"


def collect_config_issues() -> list[str]:
    load_backend_env()
    issues: list[str] = []
    required = ("SQL_DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY")
    for name in required:
        if not os.getenv(name, "").strip():
            issues.append(f"{name} 未配置")

    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if jwt_secret and len(jwt_secret) < 32:
        issues.append("JWT_SECRET_KEY 长度应至少为 32")

    llm_values = [os.getenv(name, "").strip() for name in ("API_KEY", "MODEL_NAME", "API_URL")]
    if any(llm_values) and not all(llm_values):
        issues.append("LLM 配置不完整：API_KEY、MODEL_NAME、API_URL 必须同时配置")

    alipay_values = [
        os.getenv(name, "").strip()
        for name in ("ALIPAY_APP_ID", "ALIPAY_PRIVATE_KEY_PATH", "ALIPAY_PUBLIC_KEY_PATH")
    ]
    if any(alipay_values) and not all(alipay_values):
        issues.append("支付宝配置不完整：APP_ID、应用私钥、支付宝公钥必须同时配置")
    return issues


async def check_database() -> list[str]:
    from sqlalchemy import text
    from backend.model import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(text("SELECT version FROM schema_version ORDER BY version"))
            ).scalars().all()
    except Exception as exc:
        return [f"数据库连接或 schema_version 查询失败：{exc.__class__.__name__}"]

    versions = {str(value) for value in rows}
    if EXPECTED_SCHEMA_VERSION not in versions:
        return [f"数据库未升级到 {EXPECTED_SCHEMA_VERSION}，请按顺序执行 database SQL"]
    return []


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-db", action="store_true", help="只读连接数据库并检查迁移版本")
    args = parser.parse_args()

    issues = collect_config_issues()
    if args.check_db and not any(item.startswith("SQL_DATABASE_URL") for item in issues):
        issues.extend(await check_database())

    if issues:
        print("预检未通过：")
        for item in issues:
            print(f"- {item}")
        return 1
    print("预检通过：环境配置完整" + ("，数据库已升级" if args.check_db else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
