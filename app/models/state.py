from typing import Annotated, Sequence, TypedDict, List, Union, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from dataclasses import dataclass
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_query: str
    context_text: Optional[str] 
    is_valid: bool
    iteration_count: int
    global_iteration: int
    answer_satisfied: bool

class ChatRequest(TypedDict):
    """Chat request model"""
    message: str
    session_id: str

class ChatResponse(TypedDict):
    """Chat response model"""
    response: str
    session_id: str
    status: str

@dataclass
class QueryResponses:
    final_response: str
    messages: List[Union[HumanMessage, AIMessage, ToolMessage, str]]