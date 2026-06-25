# backend/agents/marketing.py
import asyncio
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.messages import AIMessage, SystemMessage
from core.state import AgentState
from tools.marketing_tools import get_tavily_search_tool 
from db.session import SessionLocal
from db.models import User
from core.llm import llm, get_text_only_history

# 1.  THE HYBRID SCHEMA: Handles Post-Search Intents
class SearchSlots(BaseModel):
    specialty: str = Field(description="The requested specialty (e.g., 'Cardiologist', 'Dermatologist'). Extract from the FULL conversation history if mentioned earlier. ONLY default to 'medical clinics' if it is truly unspecified anywhere in the conversation.")
    specialty_was_inferred: bool = Field(description="True if you found the specialty from earlier in the conversation history. False if the user explicitly stated it in their latest message or it was not found at all.")
    explicit_location: Optional[str] = Field(description="The explicitly mentioned city or area. Leave empty if none is provided in the recent chat.")
    agreed_to_saved_location: bool = Field(description="True ONLY if the assistant previously asked to use the saved database location and the user agreed.")
    wants_to_book: bool = Field(description="CASE 1: True ONLY if the PREVIOUS assistant message already listed specific clinic names/addresses (i.e. real search results were shown) AND the user is now responding to confirm, book, or get directions to one of them. NEVER true if the user is merely asking to find/search/look for a specialist or clinic for the first time — that is a NEW search request, not a booking confirmation.")
    declined_offer: bool = Field(description="CASE 2: True ONLY if the PREVIOUS assistant message already listed specific clinic names/addresses AND the user explicitly says 'no' or declines the offer to book/get directions to one of them.")

def save_location_sync(user_id: str, final_location: str):
    """Saves location to database synchronously."""
    db = SessionLocal()
    try:
        current_patient = db.query(User).filter(User.user_id == user_id).first()
        if current_patient:
            current_patient.location = final_location
            db.commit()
            print(f"📍 [DB Persistence] Captured new location sync mapping: {final_location} for user {user_id}")
    except Exception as db_err:
        db.rollback()
        print(f"⚠️ [DB Persistence Error]: {db_err}")
    finally:
        db.close()

async def marketing_agent_node(state: AgentState):
    profile = state.get("patient_history", {}) or state.get("user_profile", {})
    db_location = profile.get("location", "") 
    user_id = state.get("user_id") 
    messages = state.get("messages", [])
    
    safe_messages = get_text_only_history(messages)

    print("🧠 [Marketing Agent] Extracting search slots & checking booking intents...")
    structured_extractor = llm.with_structured_output(SearchSlots)
    
    extraction_prompt = SystemMessage(content=f"""
    You are a Medical Concierge extracting search parameters and user intents.
    SAVED DATABASE LOCATION: {db_location if db_location else "None"}
    
    CRITICAL RULES:
    1. If the user explicitly names a city/area in their latest message, put it in `explicit_location`. NEVER guess, assume, or default a location (e.g. do NOT assume USA, do NOT invent a city) — if no city/area is explicitly stated anywhere in the conversation, leave `explicit_location` empty.
    2. If the user just says "yes" or "sure" to searching in the SAVED DATABASE LOCATION, set `agreed_to_saved_location` to True.
    3. For `specialty`: scan the ENTIRE conversation history. If the user mentioned a symptom, condition, or specialist type at any point (e.g. "I have chest pain", "I need a cardiologist", "my back hurts"), infer the appropriate specialty from that and set `specialty_was_inferred` to True. If the user has only said something generic like "find me clinics" or "find a specialist" with no symptom or specialty type anywhere in the conversation, you MUST output the exact literal string "medical clinics" for `specialty` (not a paraphrase like "general clinic" or "clinics") so the system can detect it is still missing.
    """)
    
    try:
        extracted = await structured_extractor.ainvoke([extraction_prompt] + safe_messages)
    except Exception as e:
        print(f"⚠️ [Marketing Agent] Extraction Failed: {e}")
        extracted = SearchSlots(specialty="medical clinics", specialty_was_inferred=False, explicit_location=None, agreed_to_saved_location=False, wants_to_book=False, declined_offer=False)

    # DETERMINISTIC SAFETY GATE: Check RAW messages to ensure [CLINIC_RESULTS] tag is never missed due to content sanitization.
    last_assistant_msg = next((str(msg.content) for msg in reversed(messages) if msg.type == "ai"), "")
    has_prior_clinic_results = "[CLINIC_RESULTS]" in last_assistant_msg or "[CLINIC_RESULTS_SHOWN]" in last_assistant_msg

    if not has_prior_clinic_results:
        if extracted.wants_to_book or extracted.declined_offer:
            print(" [Marketing Agent] Overriding LLM intent: no prior clinic results found, forcing wants_to_book/declined_offer to False.")
        extracted.wants_to_book = False
        extracted.declined_offer = False

    # POST-SEARCH RESOLUTION (Cases 1 & 2)
    
    # CASE 1: Hardcoded booking confirmation
    if extracted.wants_to_book:
        print("📅 [Marketing Agent] Booking intent detected. Sending hardcoded confirmation.")
        hardcoded_msg = "[NEXT_QUESTION: Okay, we have your contact details and our team will reach out to you shortly to confirm your appointment.]"
        return {"messages": [AIMessage(content=hardcoded_msg)], "last_active_node": "MarketingAgent"}

    # CASE 2: Dynamic LLM declination
    if extracted.declined_offer:
        print("[Marketing Agent] User declined offer. Generating dynamic closing question...")
        voice_prompt = SystemMessage(content="The user declined the offer to book a clinic or get directions. Write a warm, 1-sentence conversational response acknowledging this (e.g., 'No problem at all!') and asking if they have any other health questions you can assist with. Output ONLY the sentence without brackets.")
        try:
            dynamic_q = await llm.ainvoke([voice_prompt])
            closing_msg = f"[NEXT_QUESTION: {dynamic_q.content.strip()}]"
        except Exception:
            closing_msg = "[NEXT_QUESTION: No problem at all! Do you have any other health queries I can assist you with today?]"
            
        return {"messages": [AIMessage(content=closing_msg)], "last_active_node": "MarketingAgent"}

    # 2. HYBRID LOGIC GATE (Case 3 / Normal Flow)

    final_location = extracted.explicit_location
    if not final_location and extracted.agreed_to_saved_location and db_location:
        final_location = db_location

    # Determine what information is still missing
    generic_specialty_terms = {"medical clinics", "medical clinic", "clinic", "clinics", "general clinic", "general clinics"}
    specialty_missing = not extracted.specialty or extracted.specialty.strip().lower() in generic_specialty_terms
    location_missing = not final_location

    if specialty_missing or location_missing:
        print(f"[Marketing Agent] Missing info — specialty_missing={specialty_missing}, location_missing={location_missing}. Generating dynamic question...")

        if specialty_missing and location_missing:
            voice_prompt = SystemMessage(content=(
                "The user wants to find a clinic but we don't know what type of specialist they need or what city/area in India to search in. "
                "Write a warm, 1-sentence conversational question asking them both: what type of specialist or clinic they are looking for, "
                "and which city or area in India they would like to search in. Output ONLY the question without brackets."
            ))

        elif specialty_missing:
            if db_location and db_location.lower() != "none":
                voice_prompt = SystemMessage(content=(
                    f"The user wants to find a clinic. We have their location saved as '{db_location}'. "
                    "However, we don't know what type of specialist or clinic they are looking for. "
                    "Write a warm, 1-sentence conversational question asking what type of specialist or clinic they need "
                    f"and confirming if they want to search in '{db_location}' or a different area. "
                    "Output ONLY the question without brackets."
                ))
            else:
                voice_prompt = SystemMessage(content=(
                    "The user wants to find a clinic but we don't know what type of specialist they need or what city in India to search in. "
                    "Write a warm, 1-sentence conversational question asking what type of specialist or clinic they are looking for "
                    "and which city or area in India they would like to search in. Output ONLY the question without brackets."
                ))

        else:
            if db_location and db_location.lower() != "none":
                voice_prompt = SystemMessage(content=(
                    f"The user wants to find a {extracted.specialty}. We have their location saved as '{db_location}'. "
                    f"Write a warm, 1-sentence conversational question asking if they want to search for a {extracted.specialty} "
                    f"in '{db_location}' or if they prefer a different area. Output ONLY the question without brackets."
                ))
            else:
                voice_prompt = SystemMessage(content=(
                    f"The user wants to find a {extracted.specialty}. We don't know their city. "
                    "Write a warm, 1-sentence conversational question asking which city or area in India they want to search in. "
                    "Output ONLY the question without brackets."
                ))

        try:
            dynamic_q = await llm.ainvoke([voice_prompt])
            return {
                "messages": [AIMessage(content=f"[NEXT_QUESTION: {dynamic_q.content.strip()}]")], 
                "last_active_node": "MarketingAgent"
            }
        except Exception:
            return {"messages": [AIMessage(content="[NEXT_QUESTION: Could you let me know what type of clinic you're looking for and which city or area you'd like me to search in?]")], "last_active_node": "MarketingAgent"}

    # 3. EXECUTE SEARCH (Directly via City/Area Name, scoped to India)
    location_for_search = final_location if "india" in final_location.lower() else f"{final_location}, India"

    # specific search query to get clinic-level details instead of just hospital names
    search_query = f"best {extracted.specialty} clinic phone number address {location_for_search}".strip()
    print(f"\n🔍 [Marketing Agent] Scrape initializing for: '{search_query}'...")
    
    try:
       
        tavily_tool = get_tavily_search_tool(max_results=7, search_depth="advanced")
        live_web_data = await tavily_tool.ainvoke(search_query)
        
        
        if not live_web_data or len(str(live_web_data)) < 200:
            live_web_data = f"No relevant live search results were found for {final_location}."
    except Exception as e:
        print(f"🚨 [Marketing Agent] Tavily API execution failed! Error: {e}")
        live_web_data = f"System error: Unable to connect to live web directory for {final_location}."

    # 4. Extract results and dynamically generate the follow-up question
    extraction_prompt = SystemMessage(content=f"""
    You are a Medical Concierge. 
    
    YOUR TASKS:
    1. Extract the names, addresses, and contact info for the clinics found in the RAW DATA and present them clearly.
    2. 🛑 NEVER INVENT CLINICS: Only list a clinic if its name AND a real street address (not just a city name) are explicitly present in the RAW DATA below. Do NOT fabricate placeholder names, addresses, or generic examples (e.g. "Clinic A, 123 Main St"). If a clinic has no phone number or specific street address, SKIP it entirely. If the RAW DATA does not contain enough real, specific clinic details, say so plainly instead of making something up.
    3. If the RAW DATA says "System error" or "No relevant live search", politely explain you cannot access the directory right now and suggest they try a slightly different city/area name.
    4. At the very bottom, generate a natural, conversational follow-up question asking if the user wants to book an appointment or get directions to any of these locations (only ask this if real clinics were actually found). You MUST wrap this question in the [NEXT_QUESTION: ...] tag.
    
    RAW DATA:
    {live_web_data}
    """)
    
    response = await llm.ainvoke([extraction_prompt] + safe_messages)
    clean_output = str(response.content)
    
    formatted_output = f"[CLINIC_RESULTS]:\n\n{clean_output}"
    
    return {
        "messages": [AIMessage(content=formatted_output)],
        "sender": "MarketingAgent",
        "last_active_node": "MarketingAgent"
    }