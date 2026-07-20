"""Shared result contract and controlled exceptions for Agent tools."""

from __future__ import annotations

import json
from typing import Any


class ToolExecutionError(Exception):
    """A known tool failure that is safe to expose to the Agent."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def serialize_tool_result(
    *,
    tool: str,
    success: bool,
    code: str,
    message: str,
    data: Any = None,
) -> str:
    """Serialize every tool observation with the same JSON envelope."""
    return json.dumps(
        {
            "success": success,
            "code": code,
            "message": message,
            "data": data,
            "tool": tool,
        },
        ensure_ascii=False,
        default=str,
    )
