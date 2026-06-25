# backend/main.py
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional
from typing import Any
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Internal module mapping anchors
from core.state import AgentState
from core.workflow import app as agent_graph
from db.models import User, MedicalHistory, UserMedication, UserAllergy
from db.session import SessionLocal, init_db
from langchain_core.messages import HumanMessage
from memory.summarizer import compress_chat_history
from memory.episodic_memory import episodic_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Normalized Database Tables...")
    init_db()
    yield

app = FastAPI(title="Healthcare Multi-Agent Backend Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Enhanced Pydantic Validation Blueprints ---
class OnboardPayload(BaseModel):
    phone_number: str
    name: str
    age: int
    location: str
    gender: str
    lifestyle_type: str
    bmi: float
    smoking_status: str
    conditions: List[str] = []
    medications: List[str] = []
    allergies: List[str] = []
    severity: Optional[str] = "None"

class ChatPayload(BaseModel):
    user_id: str
    message: str
    image_base64: Optional[str] = None  # 👁️ Newly added for Multimodal Support

# --- Helper Functions for Background Execution ---
def update_episodic_memory_bg(user_id: str, messages: list):
    """Saves the dense summary into FAISS."""
    try:
        dense_summary = compress_chat_history(messages)
        episodic_db.add_memory(
            user_id=user_id, 
            session_id="session_current", 
            summary=dense_summary
        )
    except Exception as memory_err:
        print(f"⚠️ [Memory Error] Failed to log episodic memory: {memory_err}")

def trigger_memory_compression(user_id: str):
    """Fetches the completed chat history natively from LangGraph after the stream ends."""
    try:
        print("🧠 [Background] Fetching completed state for long-term episodic memory...")
        config = {"configurable": {"thread_id": user_id}}
        state = agent_graph.get_state(config)
        messages = state.values.get("messages", [])
        
        # Execute the summarizer
        update_episodic_memory_bg(user_id, messages)
    except Exception as e:
        print(f"⚠️ [Memory Error] Background compression trigger failed: {e}")

# --- REST Endpoints ---

@app.get("/users/phone/{phone_number}")
def check_phone_exists(phone_number: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if user:
            return {"exists": True, "user_id": user.user_id, "name": user.name}
        return {"exists": False}
    finally:
        db.close()

@app.post("/users/onboard", status_code=status.HTTP_201_CREATED)
def onboard_user(payload: OnboardPayload):
    db = SessionLocal()
    try:
        phone_exists = db.query(User).filter(User.phone_number == payload.phone_number).first()
        if phone_exists:
            raise HTTPException(status_code=400, detail="This contact track is already registered.")

        internal_id = f"pat_{uuid.uuid4().hex[:8]}"

        new_user = User(
            user_id=internal_id,
            phone_number=payload.phone_number,
            name=payload.name,
            location=payload.location,
            age=payload.age,
            gender=payload.gender,
            lifestyle_type=payload.lifestyle_type,
            bmi=payload.bmi,
            smoking_status=payload.smoking_status,
            risk_score="Low",
            engagement_score=100
        )
        db.add(new_user)

        for cond in payload.conditions:
            db.add(MedicalHistory(user_id=internal_id, condition=cond, severity=payload.severity, chronic_flag=True))

        for med in payload.medications:
            db.add(UserMedication(user_id=internal_id, medication_name=med))

        for allergy in payload.allergies:
            atype = "Drug" if allergy in ["Penicillin", "Sulfa Drugs", "Aspirin", "NSAIDs"] else "Environmental/Food"
            db.add(UserAllergy(user_id=internal_id, allergy_name=allergy, allergy_type=atype))

        db.commit()
        return {"status": "success", "message": f"Clinical portfolio verified under execution ID: {internal_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/chat")
async def run_agent_mesh(payload: ChatPayload, background_tasks: BackgroundTasks):
    """Triggers the LangGraph execution mesh and streams the LLM output. Now 100% Multimodal!"""
    try:
        # 1. Structure the content array natively for LangChain
        content: list[dict[str, Any]] = [{"type": "text", "text": payload.message}]
        
        # 2. Append the image block if the user attached a file
        if payload.image_base64:
            print("👁️ [Main Router] Base64 Image payload received. Packaging as multimodal HumanMessage.")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{payload.image_base64}"}
            })
            
        # 3. Create the multimodal human message
        new_message = HumanMessage(content=content)

        # 4. Inject into the graph state
        graph_inputs = {
            "messages": [new_message],
            "user_id": payload.user_id
        }
        config = {"configurable": {"thread_id": payload.user_id}}

        # Create the asynchronous generator
        async def token_generator():
            # astream_events listens to everything happening inside the graph
            async for event in agent_graph.astream_events(graph_inputs, config, version="v2"):
                # Filter for LLM streaming tokens
                if event["event"] == "on_chat_model_stream":
                    # CRITICAL: Only yield tokens if they come from the final Compliance Agent
                    if event["metadata"].get("langgraph_node") == "ComplianceAgent":
                        chunk = event["data"]["chunk"].content
                        if chunk:
                            yield chunk

        # Queue the summarizer to run exactly when the stream finishes
        background_tasks.add_task(trigger_memory_compression, payload.user_id)

        # Return the StreamingResponse so Streamlit can read it live
        return StreamingResponse(token_generator(), media_type="text/event-stream")

    except Exception as e:
        import traceback
        print("❌ CRITICAL ERROR IN CHAT ENGINE EXECUTION TURN:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/users/profile/{user_id}")
def get_user_profile(user_id: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        conds = [c.condition for c in db.query(MedicalHistory).filter(MedicalHistory.user_id == user_id).all()]
        meds = [m.medication_name for m in db.query(UserMedication).filter(UserMedication.user_id == user_id).all()]
        algs = [a.allergy_name for a in db.query(UserAllergy).filter(UserAllergy.user_id == user_id).all()]
        
        return {
            "name": user.name,
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "lifestyle_type": user.lifestyle_type,
            "bmi": user.bmi,
            "smoking_status": user.smoking_status,
            "conditions": conds,
            "medications": meds,
            "allergies": algs,
            "phone_number": user.phone_number
        }
    finally:
        db.close()

@app.put("/users/profile/{user_id}")
def update_user_profile(user_id: str, payload: OnboardPayload):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update Base Profile
        user.name = payload.name
        user.age = payload.age
        user.gender = payload.gender
        user.location = payload.location
        user.lifestyle_type = payload.lifestyle_type
        user.bmi = payload.bmi
        user.smoking_status = payload.smoking_status
        
        # Clear out old lists to prevent duplicates
        db.query(MedicalHistory).filter(MedicalHistory.user_id == user_id).delete()
        db.query(UserMedication).filter(UserMedication.user_id == user_id).delete()
        db.query(UserAllergy).filter(UserAllergy.user_id == user_id).delete()
        
        # Insert newly updated lists
        for cond in payload.conditions:
            db.add(MedicalHistory(user_id=user_id, condition=cond, severity=payload.severity, chronic_flag=True))
        for med in payload.medications:
            db.add(UserMedication(user_id=user_id, medication_name=med))
        for allergy in payload.allergies:
            atype = "Drug" if allergy in ["Penicillin", "Sulfa Drugs", "Aspirin", "NSAIDs"] else "Environmental/Food"
            db.add(UserAllergy(user_id=user_id, allergy_name=allergy, allergy_type=atype))
            
        db.commit()
        return {"status": "success", "message": "Profile updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)