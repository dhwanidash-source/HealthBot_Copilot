# backend/agents/patient.py
import asyncio
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from core.state import AgentState
from memory.rag_store import rag_db
from db.session import SessionLocal
from db.models import User
from core.llm import llm, vision_llm, get_text_only_history


# 1. SCHEMA
class ClinicalTriage(BaseModel):
    is_triage_complete: bool = Field(description="True if user says 'no'/'none'/'no such symptoms', or you have enough info to recommend a specialist. False otherwise.")
    diagnosis_summary: str = Field(default="", description="Likely cause, self-care steps, red-flag warnings as bullet points. Empty string when ending triage.")
    triage_severity: str = Field(default="", description="One of: LOW, MODERATE, HIGH, CRITICAL_EMERGENCY. Empty string when ending triage.")
    suggested_specialist: str = Field(default="", description="Specific specialist e.g. Neurologist, Cardiologist. Use General Physician if unsure.")
    dynamic_follow_up: str = Field(description="2-3 symptom questions as bullet list if triaging. If triage complete: 'Would you like me to help you find a [specialist] nearby?' — always name the specialist.")
    found_in_guidelines: bool = Field(description="True if the guidelines context contains a relevant answer.")
    source_guideline: str = Field(default="", description="Guideline filename if found, else empty string.")
    source_page: str = Field(default="", description="Page number if found, else empty string.")


def fetch_user_location(user_id: str) -> str:
    with SessionLocal() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        return user.location.strip() if user and user.location else None


def fetch_rag_guidelines(query: str) -> str:
    return rag_db.search_guidelines(query=query, k=2)


async def patient_agent_node(state: AgentState):
    """Clinical Triage Node: Handles Symptoms AND Medical Documents Dynamically."""
    messages = state.get("messages", [])
    user_id = state.get("user_id", "anonymous_vault")

    # 1. MULTIMODAL ROUTER
    has_image = False
    user_query = ""

    last_human_msg = next((msg for msg in reversed(messages) if msg.type == "human"), None)
    if last_human_msg:
        content = last_human_msg.content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if "image" in part.get("type", ""):
                        has_image = True
                    elif part.get("type") == "text":
                        user_query += part.get("text", "") + " "
        else:
            user_query = str(content)
    user_query = user_query.strip()

    print("\n" + "="*40)
    print(f"🚨 DEBUG - HAS IMAGE: {has_image} | QUERY: {user_query}")
    print("="*40 + "\n")

    # PARALLEL: start location fetch early
    location_task = asyncio.create_task(asyncio.to_thread(fetch_user_location, user_id))
    structured_llm = llm.with_structured_output(ClinicalTriage)
    safe_messages = get_text_only_history(messages)

    # 2. BUILD CONTEXT
    if has_image:
        print("👁️ [Patient Agent] Document uploaded! Executing Vision Pipeline...")
        vision_prompt = SystemMessage(content=f'You are a medical document extractor. The user asks: "{user_query}". Extract the relevant text, medicine names, or data from the image.')
        try:
            vision_raw = await vision_llm.ainvoke([vision_prompt] + list(messages))
            image_findings = str(vision_raw.content)
            print(f"📄 Vision saw: {image_findings[:100]}...")
        except Exception as e:
            image_findings = "The image was unreadable or an error occurred."
            print(f"⚠️ Vision error: {e}")

        context_block = f"DOCUMENT FINDINGS:\n{image_findings[:1200]}"
        rules = (
            "1. Answer the user's question using ONLY the document findings above. Put answer in diagnosis_summary.\n"
            "2. Set is_triage_complete to true.\n"
            "3. In dynamic_follow_up: ask if they have other questions or want to find a specialist."
        )
    else:
        print("⚕️ [Patient Agent] Text query — searching RAG...")
        raw = await asyncio.to_thread(fetch_rag_guidelines, user_query)
        context_block = f"GUIDELINES:\n{raw[:1200]}"
        rules = (
            "1. DIAGNOSE FIRST (MANDATORY): On EVERY turn where the user describes a symptom or health concern, "
            "you MUST fill diagnosis_summary with: likely cause(s), practical self-care steps, and red-flag warning signs. "
            "Bullet points preferred. NEVER leave diagnosis_summary empty on the first response to a health query.\n"
            "2. THEN FOLLOW-UP (MANDATORY): After diagnosing, ALWAYS use dynamic_follow_up to ask 2-3 specific symptom "
            "questions as a bullet list to narrow the diagnosis further. Never repeat questions already asked in the chat history.\n"
            "3. ENDING TRIAGE ONLY: If the user explicitly says no/none/no such symptoms in response to your follow-up questions — "
            "ONLY THEN set is_triage_complete to true, leave diagnosis_summary as empty string, "
            "set suggested_specialist to the correct specialist. In dynamic_follow_up ask: "
            "'Would you like me to help you find a [specialist] nearby?' — always name the specialist explicitly."
        )

    # 3. INVOKE
    system_prompt = SystemMessage(content=f"You are a Clinical Assistant.\n\n{context_block}\n\nRULES:\n{rules}\n\nOutput ONLY the function call.")

    try:
        response = await structured_llm.ainvoke([system_prompt] + safe_messages)
    except Exception as e:
        print(f"⚠️ [Patient Agent] Structured call failed: {e}")
        return {"messages": [AIMessage(content="[NEXT_QUESTION: I am having a little trouble processing that. Could you rephrase your question?]")], "last_active_node": "PatientAgent"}

    # 4. DETERMINISTIC ENFORCEMENT: wipe diagnosis fields if triage is complete, regardless of LLM output
    if response.is_triage_complete:
        response.diagnosis_summary = ""
        response.triage_severity = ""
        response.source_guideline = ""
        response.source_page = ""
        print("✅ [Patient Agent] Triage complete — diagnosis fields cleared.")

    # 6. WEB SEARCH FALLBACK
    if not response.found_in_guidelines and response.diagnosis_summary.strip() and not response.is_triage_complete:
        print("🌐 [Patient Agent] Not in guidelines — triggering web search...")
        try:
            search = TavilySearchResults(max_results=3)
            web_results = await search.ainvoke(user_query)
            response.diagnosis_summary = f"Based on recent medical literature: {' '.join([r['content'] for r in web_results][:2])}"
            response.source_guideline = "External Medical Directories"
            response.source_page = "Web"
        except Exception:
            pass

    # 7. FORMAT OUTPUT
    db_location = await location_task
    location_flag = ""
    if response.is_triage_complete and response.suggested_specialist and response.suggested_specialist.lower() not in ("", "none"):
        if not db_location:
            location_flag = "\n[MISSING_INFO: Location]"

    formatted_output = ""
    if response.diagnosis_summary.strip():
        formatted_output += (
            f"[CLINICAL_DIAGNOSIS]: {response.diagnosis_summary}\n"
            f"[SEVERITY]: {response.triage_severity}\n"
            f"[SPECIALIST]: {response.suggested_specialist}\n"
        )
        if response.source_guideline:
            formatted_output += f"\n---\n**📚 Source:** {response.source_guideline} | Page: {response.source_page or 'N/A'}\n"

    formatted_output += f"\n[NEXT_QUESTION: {response.dynamic_follow_up}]\n{location_flag}"

    return {"messages": [AIMessage(content=formatted_output.strip())], "last_active_node": "PatientAgent"}