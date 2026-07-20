import os
from typing import Annotated, TypedDict, Any

from backend.env import load_backend_env
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

load_backend_env()

class react_format(TypedDict):
    thought : list[str]
    action: list[str]
    action_args: list[str]
    observation: list[str]
    round : int

class input_format(TypedDict):
    input: str
    memory: dict[str,list[dict[str,Any]]]

"""
閲嶆瀯涓€涓婫raphState鐨勬牸寮忓拰浠ｇ爜
{
    'user_input' : str,
    
    user_id : int,
    session_id : int,
    
    'thought' : str
    'action' : str,
    'action_args' : ,
    'messages' : list[ToolMessage]锛? #鐢ㄤ簬瀛樺墠鍑犺疆鐨刼bservation
    'round' : int,
    
    final_result : str
}
"""


class GraphState(TypedDict):
    """State for the multi-agent workflow."""

    user_input: str

    user_id: int
    session_id: int

    thought: str
    action: str
    action_args: dict
    tool_call_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    round: int

    final_result: str



model = os.getenv('MODEL_NAME')
api_key = os.getenv('API_KEY')
base_url = os.getenv('API_URL')















