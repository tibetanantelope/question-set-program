import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.env import load_backend_env
from sqlalchemy.orm.decl_api import declarative_base

load_backend_env()

SQLALCHEMY_DATABASE_URL = os.getenv("SQL_DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        f"SQL_DATABASE_URL is empty. Please check {str(SQLALCHEMY_DATABASE_URL)} (backend/.env)."
    )

# 鍏煎锛氬鏋滈厤缃簡鍚屾椹卞姩 pymysql锛屼絾浠ｇ爜浣跨敤鐨勬槸 create_async_engine锛?
# 浼氬鑷?"asyncio extension requires an async driver to be used"銆?
# 鐩墠 requirements.txt 宸插畨瑁?asyncmy锛屽洜姝よ繖閲岃嚜鍔ㄦ浛鎹负 mysql+asyncmy銆?
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("mysql+pymysql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "mysql+pymysql://",
        "mysql+asyncmy://",
        1,
    )

# 鍒涘缓寮傛寮曟搸锛堢鐞嗚繛鎺ユ睜锛?
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # 鎵撳嵃 SQL 璇彞锛堝紑鍙戝紑鍚紝鐢熶骇鍏抽棴锛?
    pool_pre_ping=True,  # 鑷姩鏍￠獙杩炴帴鏈夋晥鎬?
    pool_size=10,  # 杩炴帴姹犲ぇ灏忥紙鐢熶骇鎸夐渶璋冩暣锛?
)

# 寮傛浼氳瘽宸ュ巶
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 鎻愪氦鍚庝笉澶辨晥 ORM 瀵硅薄
    autoflush=False,
    autocommit=False,
)#type:ignore

# ORM 妯″瀷鍩虹被
Base = declarative_base()

# 渚濊禆鍑芥暟锛氳幏鍙栧紓姝ユ暟鎹簱浼氳瘽锛堣嚜鍔ㄥ紑闂繛鎺ワ級
async def get_db() -> AsyncSessionLocal:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()