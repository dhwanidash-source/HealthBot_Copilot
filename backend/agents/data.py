# backend/agents/data.py
from core.state import AgentState
from memory.episodic_memory import episodic_db 

# Import your database session and models
from db.session import SessionLocal
from db.models import User, MedicalHistory, UserMedication, UserAllergy

def data_agent_node(state: AgentState):
    """
    Comprehensive Data Retrieval Node.
    Pulls the user's static demographic profile from SQL and merges it with 
    their dynamic long-term FAISS episodic memory.
    
    NOTE: Runs in PARALLEL with PatientAgent. Do not write to 'last_active_node' 
    here to prevent state-overwrite race conditions.
    """
    messages = state.get("messages", [])
    user_id = state.get("user_id", "unknown")
    user_query = str(messages[-1].content) if messages else ""
    
    # 1. Fetch Static Profile from SQL Database
    print(f" [Data Agent] Fetching SQL profile for {user_id}...")
    db = SessionLocal()
    sql_profile = {}
    try:
        user_record = db.query(User).filter(User.user_id == user_id).first()
        if user_record:
            # Grab all conditions, medications, and allergies mapped to this user
            conditions = [c.condition for c in db.query(MedicalHistory).filter(MedicalHistory.user_id == user_id).all()]
            medications = [m.medication_name for m in db.query(UserMedication).filter(UserMedication.user_id == user_id).all()]
            allergies = [a.allergy_name for a in db.query(UserAllergy).filter(UserAllergy.user_id == user_id).all()]
            
            sql_profile = {
                "name": user_record.name,
                "location": user_record.location,  # Pulls actual city (e.g., Delhi) for the Marketing Agent
                "age": user_record.age,
                "conditions": conditions,
                "medications": medications,
                "allergies": allergies
            }
    except Exception as e:
        print(f"⚠️ [Data Agent] SQL fetch error: {e}")
    finally:
        db.close()

    # 2. Fetch Dynamic FAISS Episodic Memory
    print(f"📚 [Data Agent] Recalling episodic memory...")
    past_context_list = episodic_db.recall_memories(user_id=user_id, query=user_query, k=2)
    past_context_str = "\n".join(past_context_list) if past_context_list else "No prior relevant history."
    
    # 3. Merge everything into the LangGraph state
    sql_profile["episodic_memory"] = past_context_str
    
    print(f"✅ [Data Agent] Profile payload compiled securely.")
    
    return {
        "patient_history": sql_profile
        
    }