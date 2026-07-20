from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from backend.agents.skills import load_skill
from backend.agents.tools.result import ToolExecutionError


class LoadSkillInput(BaseModel):
    name: str = Field(min_length=1, max_length=64, description="要加载的 Skill 名，必须在可用 Skill 列表中")


class LoadSkillTool(BaseTool):
    name: str = "load_skill_tool"
    description: str = (
        "按需加载一个 Skill（能力包）的 SKILL.md 正文到上下文中。"
        "当用户的诉求命中某个 Skill 的触发词时，应先调用本工具拿到剧本，"
        "再据此决定下一步调用哪个业务工具或直接作答。"
    )
    args_schema: Type[BaseModel] = LoadSkillInput

    def _run(self, name: str) -> str:
        try:
            body = load_skill(name)
            return f"【Skill: {name}】已加载，以下内容即该 Skill 的完整剧本：\n{body}"
        except FileNotFoundError as e:
            raise ToolExecutionError("SKILL_NOT_FOUND", f"未找到Skill：{name}") from e
        except Exception as e:
            raise ToolExecutionError("SKILL_LOAD_FAILED", "Skill加载失败") from e

    async def _arun(self, name: str) -> str:
        return self._run(name)
