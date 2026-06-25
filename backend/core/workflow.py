# backend/core/workflow.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from core.state import AgentState

# Import all agent nodes
from agents.orchestrator import orchestrator_node
from agents.patient import patient_agent_node
from agents.data import data_agent_node
from agents.personalization import personalization_agent_node
from agents.marketing import marketing_agent_node
from agents.compliance import compliance_agent_node

# 1.ROUTER: Support Fan-Out ---
def route_from_orchestrator(state: AgentState):
    """
    Reads the intent string. 
    Returns a LIST of strings to trigger parallel execution, or a single string track.
    """
    track = state.get("intent", "CHAT_TRACK")
    
    if track == "CLINICAL_TRACK":
        return ["DataAgent", "PatientAgent"]
    elif track == "SEARCH_TRACK":
        return "MarketingAgent"
    else:
        return "ComplianceAgent"

#  2. CONSTRUCT THE STATE GRAPH 
workflow = StateGraph(AgentState)

# Register Nodes
workflow.add_node("Orchestrator", orchestrator_node)
workflow.add_node("PatientAgent", patient_agent_node)
workflow.add_node("DataAgent", data_agent_node)
workflow.add_node("PersonalizationAgent", personalization_agent_node)
workflow.add_node("MarketingAgent", marketing_agent_node)
workflow.add_node("ComplianceAgent", compliance_agent_node)

# Set Entry Point
workflow.set_entry_point("Orchestrator")

# Conditional Routing from Orchestrator (Must map to the list elements)
workflow.add_conditional_edges(
    "Orchestrator",
    route_from_orchestrator,
    {
        "DataAgent": "DataAgent",       # Maps from the parallel array
        "PatientAgent": "PatientAgent",   # Maps from the parallel array
        "MarketingAgent": "MarketingAgent",
        "ComplianceAgent": "ComplianceAgent"
    }
)

workflow.add_edge("DataAgent", "PersonalizationAgent")
workflow.add_edge("PatientAgent", "PersonalizationAgent")

# Downstream flow continues linearly
workflow.add_edge("PersonalizationAgent", "ComplianceAgent")
workflow.add_edge("MarketingAgent", "ComplianceAgent")
workflow.add_edge("ComplianceAgent", END)

# Compile with Checkpointer memory
memory_checkpointer = MemorySaver()
app = workflow.compile(checkpointer=memory_checkpointer)