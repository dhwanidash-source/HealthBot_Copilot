from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==========================================
# 1. CORE HEALTH TABLES
# ==========================================

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(String, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    location = Column(String)
    lifestyle_type = Column(String)
    bmi = Column(Float) 
    smoking_status = Column(String) 
    exercise_frequency = Column(String) 
    risk_score = Column(String)
    engagement_score = Column(Integer)
    churn_risk = Column(String) 
    lifetime_value = Column(Float) 
    preferred_channel = Column(String) 
    consent_flag = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (Added explicit cascade settings for robust data safety)
    medical_history = relationship("MedicalHistory", back_populates="user", cascade="all, delete-orphan")
    medications = relationship("UserMedication", back_populates="user", cascade="all, delete-orphan") # 🆕 Added
    allergies = relationship("UserAllergy", back_populates="user", cascade="all, delete-orphan")     # 🆕 Added
    visits = relationship("Visit", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    campaign_engagements = relationship("CampaignEngagement", back_populates="user", cascade="all, delete-orphan")
    user_state = relationship("UserState", back_populates="user", uselist=False, cascade="all, delete-orphan")

class MedicalHistory(Base):
    __tablename__ = 'medical_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    condition = Column(String, nullable=False)
    severity = Column(String)
    chronic_flag = Column(Boolean, default=True)
    diagnosis_date = Column(DateTime, default=datetime.utcnow)
    
    # Note: 'medications' and 'allergies' strings have been completely removed from here.
    user = relationship("User", back_populates="medical_history")

class UserMedication(Base): 
    __tablename__ = 'user_medications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    medication_name = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="medications")

class UserAllergy(Base): 
    __tablename__ = 'user_allergies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    allergy_name = Column(String, nullable=False)
    allergy_type = Column(String) # e.g., 'Drug', 'Environmental', 'Food'
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="allergies")

class Visit(Base):
    __tablename__ = 'visits'
    
    visit_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    hospital_id = Column(String) 
    visit_date = Column(DateTime)
    purpose = Column(String)
    doctor_notes = Column(Text)
    followup_required = Column(Boolean)
    
    user = relationship("User", back_populates="visits")


# ==========================================
# 2. MEMORY & STATE TABLES (Agent Recall)
# ==========================================

class Session(Base):
    __tablename__ = 'sessions'
    
    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    channel = Column(String)
    context_summary = Column(Text) 
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    role = Column(String) # 'user', 'ai', 'tool'
    agent_name = Column(String) 
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")

class ChatSummary(Base):
    __tablename__ = 'chat_summaries'
    
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    summary_text = Column(Text)
    embedding_vector = Column(Text) 
    created_at = Column(DateTime, default=datetime.utcnow)

class UserState(Base):
    __tablename__ = 'user_state'
    
    user_id = Column(String, ForeignKey('users.user_id'), primary_key=True)
    latest_conditions = Column(String) 
    risk_score = Column(String)
    engagement_score = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="user_state")


# ==========================================
# 3. MARKETING & INTELLIGENCE TABLES
# ==========================================

class Campaign(Base):
    __tablename__ = 'campaigns'
    
    campaign_id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    target_segment = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    budget = Column(Float)

class CampaignEngagement(Base):
    __tablename__ = 'campaign_engagement'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    campaign_id = Column(String, ForeignKey('campaigns.campaign_id'), nullable=False)
    opened = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    converted = Column(Boolean, default=False)
    last_interaction = Column(DateTime)
    
    user = relationship("User", back_populates="campaign_engagements")

class Segment(Base):
    __tablename__ = 'segments'
    
    id = Column(String, primary_key=True) # Changed from segment_id for consistency
    description = Column(Text)
    criteria_json = Column(JSON) 


# ==========================================
# 4. SYSTEM LOGS
# ==========================================

class AgentLog(Base):
    __tablename__ = 'agent_logs'
    
    id = Column(String, primary_key=True)
    session_id = Column(String)
    agent_name = Column(String)
    input = Column(Text)
    output = Column(Text)
    execution_time = Column(Float)