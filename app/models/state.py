from typing import Annotated, Sequence, TypedDict, List, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages
from dataclasses import dataclass

class AgentState(TypedDict):
    """State model for the chatbot agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_query: str
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