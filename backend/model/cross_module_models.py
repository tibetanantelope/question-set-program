"""跨模块模型的兼容导出。

这些表的唯一 ORM 定义归成员三的 ``backend.model.mastery`` 所有。
成员四只读取这些表，不应再次向同一个 ``Base.metadata`` 注册同名表。
"""

from backend.model.mastery import KnowledgeMastery, Mistake, ReviewPlan

__all__ = ["KnowledgeMastery", "Mistake", "ReviewPlan"]
