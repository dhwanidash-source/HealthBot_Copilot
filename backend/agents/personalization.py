# backend/agents/personalization.py
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.messages import AIMessage, SystemMessage
from core.state import AgentState
import groq
from core.llm import llm, get_text_only_history

class PersonalizedReview(BaseModel):
    personalized_advice: str = Field(description="Actionable, personalized health/lifestyle advice. If the diagnosis includes lab results or document analysis, provide specific dietary or habit changes targeting those exact findings based on the user's profile.")
    contraindications_found: str = Field(description="Set STRICTLY to the string 'true' if the advice, or any newly uploaded prescription drugs, conflict dangerously with the patient's existing medications or chronic conditions. Otherwise 'false'.")
    safety_warning: str = Field(default="", description="If contraindications_found is 'true', provide a highly clear medical safety warning. Otherwise, leave empty.")
    follow_up_question: str = Field(default="", description="A natural follow-up question regarding their specific medical routine. If none needed, leave blank.")

async def personalization_agent_node(state: AgentState):
    """Takes generic clinical guidelines or document analysis and personalizes it to the user's specific profile."""
    messages = state.get("messages", [])
    safe_messages = get_text_only_history(messages)
    
    # Grab the output from the Patient Agent using sanitized history
    basic_diagnosis = str(safe_messages[-1].content) if safe_messages else ""
    
    # THE BYPASS FIX: If no clinical data is present, skip
    if "[CLINICAL_DIAGNOSIS]" not in basic_diagnosis:
        return {"messages": [AIMessage(content=basic_diagnosis)], "last_active_node": "PersonalizationAgent"}

    profile = state.get("patient_history", {}) or state.get("user_profile", {})
    age = profile.get("age", "Unknown")
    conditions = profile.get("conditions", [])
    medications = profile.get("medications", [])
    allergies = profile.get("allergies", [])
    lifestyle = profile.get("lifestyle_type", "Unknown")
    
    structured_llm = llm.with_structured_output(PersonalizedReview)
    
    personalization_prompt = SystemMessage(content=f"""
    You are a Precision Medicine Specialist. You MUST output using the provided tool schema.
    
    RAW CLINICAL DATA / DOCUMENT ANALYSIS:
    "{basic_diagnosis}"
    
    PATIENT PROFILE:
    - Age: {age}
    - Chronic Conditions: {conditions}
    - Active Medications: {medications}
    - Known Allergies: {allergies}
    - Lifestyle: {lifestyle}
    
    YOUR TASK:
    1. Cross-reference the RAW CLINICAL DATA with the patient profile.
    2. Flag 'true' for contraindications_found if any suggestions (or drugs listed in an uploaded prescription) are dangerous given their background.
    3. Generate highly specific personalized advice. 
       - If the RAW CLINICAL DATA contains lab results (e.g., high cholesterol), give them targeted dietary/lifestyle tips based on their specific age and lifestyle.
       - If it contains a prescription, give them tips on taking it safely with their other medications.
    4. CRITICAL: If the RAW CLINICAL DATA already contains a follow-up question, DO NOT write a new one. Leave 'follow_up_question' blank to avoid overwhelming the user.
    
    🚨 CRITICAL TOOL INSTRUCTION:
    You MUST output your decision by calling the provided function matching the PersonalizedReview schema. Output ONLY the function call.
    """)
    
    print("🧬 [Personalization Agent] Analyzing profile against clinical targets/documents...")
    try:
        # Pass safe_messages here!
        response = await structured_llm.ainvoke([personalization_prompt] + safe_messages)
        has_contraindication = response.contraindications_found.strip().lower() in ["true", "yes", "1"]
    except (groq.APIError, Exception) as e:
        print(f"⚠️ [Personalization Agent] Target fallback activated: {e}")
        response = PersonalizedReview(
            personalized_advice=f"Please continue following your primary treatment guidelines carefully.",
            contraindications_found="false", safety_warning="", follow_up_question=""
        )
        has_contraindication = False
    
    profile_summary = f"Age: {age} | Conditions: {conditions} | Medications: {medications} | Allergies: {allergies}"
    
    final_content = f"{basic_diagnosis}\n\n[PATIENT_PROFILE_USED]: {profile_summary}\n[PERSONALIZATION_INSIGHT]: {response.personalized_advice}"
    
    if has_contraindication and response.safety_warning.strip():
        final_content += f"\n[CONTRAINDICATION_WARNING]: {response.safety_warning}"
    
    if response.follow_up_question.strip():
        final_content += f"\n[NEXT_QUESTION: {response.follow_up_question.strip()}]"
    
    return {"messages": [AIMessage(content=final_content)], "last_active_node": "PersonalizationAgent"}