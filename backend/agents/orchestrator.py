# backend/agents/orchestrator.py
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage
from core.state import AgentState
from core.llm import llm, get_text_only_history

class IntentRoute(BaseModel):
    reasoning: str = Field(description="Analyze the user's latest input in the context of the previous assistant question.")
    pipeline_track: str = Field(
        description="Select the starting pipeline. Choices: 'CLINICAL_TRACK', 'SEARCH_TRACK', or 'CHAT_TRACK'."
    )

async def orchestrator_node(state: AgentState):
    """
    Semantic Intent Orchestrator with Contextual Memory and Async Fallback.
    """
    structured_planner = llm.with_structured_output(IntentRoute)
    messages = state.get("messages", [])
    safe_messages = get_text_only_history(messages)
    
    # Extract context safely using the sanitized messages
    user_input = str(safe_messages[-1].content).lower() if safe_messages else ""
    
    # Detect if the raw message had an image so we can force the clinical track
    has_image = False
    last_raw_msg = messages[-1].content if messages else ""
    if isinstance(last_raw_msg, list):
        for part in last_raw_msg:
            if isinstance(part, dict) and part.get("type") == "image_url":
                has_image = True
    
    # Grab the last assistant message to understand what the user is answering
    last_assistant_msg = ""
    for msg in reversed(safe_messages[:-1]):
        if isinstance(msg, AIMessage):
            last_assistant_msg = str(msg.content)
            break
    
    system_prompt = SystemMessage(content=f"""
    You are the Central AI Routing Director. You must look at the USER'S LATEST MESSAGE and the PREVIOUS ASSISTANT MESSAGE to determine the track.
    
    PREVIOUS ASSISTANT MESSAGE: "{last_assistant_msg}"
    USER LATEST MESSAGE: "{user_input}"
    DOCUMENT ATTACHED: {"Yes" if has_image else "No"}
    
    PIPELINE TRACKS:
    - 'CLINICAL_TRACK': 
        * User mentions physical pain, symptoms, illness, or asks for health advice.
        * OR, the user is answering a previous question about their health/symptoms.
        * OR, the user says "no" or "none" when asked about further symptoms.
        * OR, a DOCUMENT ATTACHED is 'Yes' (because the Patient Agent analyzes lab reports and prescriptions).
    - 'SEARCH_TRACK': 
        * User explicitly asks to find a doctor/clinic.
        * User agreed to a web search offer (e.g., 'yes', 'find one near me').
    - 'CHAT_TRACK': 
        * Casual greetings, thank yous, or non-medical small talk.
        
    🚨 CRITICAL TOOL INSTRUCTION (NO CONVERSATION):
    You MUST output your decision by calling the provided routing tool/function matching the IntentRoute schema.
    Do NOT output regular conversational text. 
    Do NOT explain your reasoning outside the schema. 
    Output ONLY the function call.
    """)
    
    print("\n🧭 [Orchestrator] Parsing intent with context...")
    
    try:
        plan = await structured_planner.ainvoke([system_prompt] + safe_messages)
    except Exception as e:
        print(f"⚠️ [Orchestrator] Groq Tool Calling Failed: {e}")
        print("🔄 [Orchestrator] Defaulting to CLINICAL_TRACK for safety.")
        # If the LLM tries to chat and crashes the tool, manually force the default route
        plan = IntentRoute(
            reasoning="System fallback due to LLM tool execution failure.",
            pipeline_track="CLINICAL_TRACK"
        )
        
    print(f"🧭 [Orchestrator] Routing user down -> {plan.pipeline_track}")
    
    return {
        "intent": plan.pipeline_track,
        "sender": "Orchestrator"
    }