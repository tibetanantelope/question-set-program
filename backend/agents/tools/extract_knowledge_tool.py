from typing import Type

from backend.agents.agent.extract_agent import async_extract_tool, extract_tool
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from backend.agents.tools.result import ToolExecutionError


class ExtractKnowledgeInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000, description="用户输入的题目或文本内容")

class ExtractKnowledgeTool(BaseTool):
    name : str = "extract_tool"
    description : str = "用户需要生成题目、变式题、提取知识点时调用"
    args_schema : Type[BaseModel] = ExtractKnowledgeInput

    def _run(self, text: str) -> str:
        try:
            extract_result = extract_tool(text)

            if extract_result:
                return f"""【知识点提取】已提取知识点：
                难度：{extract_result.get('difficulty', '未知')}
                知识点：{', '.join(extract_result.get('knowledge_points', []))}"""
            else:
                return "【知识点提取】未能提取到知识点"

        except Exception as e:
            raise ToolExecutionError("KNOWLEDGE_EXTRACTION_FAILED", "知识点提取失败") from e


    async def _arun(self, text: str) -> str:
        """执行知识点提取工具"""
        try:
            extract_result = await async_extract_tool(text)

            if extract_result:
                return f"""【知识点提取】已提取知识点：
                难度：{extract_result.get('difficulty', '未知')}
                知识点：{', '.join(extract_result.get('knowledge_points', []))}"""
            else:
                return "【知识点提取】未能提取到知识点"
        except Exception as e:
            raise ToolExecutionError("KNOWLEDGE_EXTRACTION_FAILED", "知识点提取失败") from e
