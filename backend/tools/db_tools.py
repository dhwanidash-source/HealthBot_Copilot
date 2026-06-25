from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import User, MedicalHistory, Visit
import json

def fetch_structured_profile(user_id: str) -> str:
    """Retrieves age, risk score, and basic profile info from SQL[cite: 398]."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return json.dumps({"error": "User not found."})
        
        profile = {
            "name": user.name,
            "age": user.age,
            "risk_score": user.risk_score,
            "lifestyle": user.lifestyle_type
        }
        return json.dumps(profile)
    finally:
        db.close()

def fetch_medical_history(user_id: str) -> str:
    """Retrieves hard facts about conditions and medications[cite: 402]."""
    db: Session = SessionLocal()
    try:
        history = db.query(MedicalHistory).filter(MedicalHistory.user_id == user_id).all()
        if not history:
            return json.dumps({"message": "No medical history found."})
        
        records = [
            {"condition": h.condition, "severity": h.severity, "medications": h.medications}
            for h in history
        ]
        return json.dumps(records)
    finally:
        db.close()

def fetch_recent_activity(user_id: str) -> str:
    """Retrieves last visit date and followup requirements[cite: 400]."""
    db: Session = SessionLocal()
    try:
        visits = db.query(Visit).filter(Visit.user_id == user_id).order_by(Visit.visit_date.desc()).limit(3).all()
        if not visits:
            return json.dumps({"message": "No recent visits found."})
        
        records = [
            {"date": str(v.visit_date), "purpose": v.purpose, "followup_required": v.followup_required}
            for v in visits
        ]
        return json.dumps(records)
    finally:
        db.close()