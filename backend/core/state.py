# backend/core/state.py
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    intent: str
    user_id: str
    patient_history: dict
    last_active_node: str # Used by ComplianceAgent to pick the next question