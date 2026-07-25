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

# 兼容：如果配置了同步驱动 pymysql，但代码使用的是 create_async_engine，
# 会导致 "asyncio extension requires an async driver to be used"。
# 目前 requirements.txt 已安装 asyncmy，因此这里自动替换为 mysql+asyncmy。
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("mysql+pymysql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "mysql+pymysql://",
        "mysql+asyncmy://",
        1,
    )

# 创建异步引擎（管理连接池）
_engine_kwargs = {"echo": False, "pool_pre_ping": True}
if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
# aiomysql 0.3.x 与 SQLAlchemy 2.0.x 的 pool_pre_ping 存在不兼容
# (ping() 缺少 reconnect 参数)，仅对 aiomysql 关闭预检以规避该缺陷；
# asyncmy / 其他驱动不受影响，仍保留连接预检。
if SQLALCHEMY_DATABASE_URL.startswith("mysql+aiomysql"):
    _engine_kwargs["pool_pre_ping"] = False
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ORM 模型基类
Base = declarative_base()


# 依赖函数：获取异步数据库会话（自动开关连接）
async def get_db() -> AsyncSessionLocal:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# 预加载所有 ORM 模型，确保 startup create_all 能发现全部表
from backend.model.user import User  # noqa: E402, F401
from backend.model.user_profile import UserProfile  # noqa: E402, F401
from backend.model.diagnostic import DiagnosticSession, DiagnosticAnswer  # noqa: E402, F401
from backend.model.learning import LearningSession, Diagnosis, Practice, Question  # noqa: E402, F401
from backend.model.mastery import AnswerRecord, KnowledgeMastery, Mistake, ReviewPlan  # noqa: E402, F401
from backend.model.learning_models import (  # noqa: E402, F401
    LearningRecord, DailyPlan, Notification, LearningReport,
)
from backend.model.cross_module_models import (  # noqa: E402, F401
    KnowledgeMastery as CrossKnowledgeMastery,
    Mistake as CrossMistake,
    ReviewPlan as CrossReviewPlan,
)
