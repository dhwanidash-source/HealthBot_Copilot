import streamlit as st
import requests
import base64
from datetime import datetime

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Healthcare Client Portal", layout="centered", page_icon="🩺")

# Modern Dark-Mode Texting App Styling
st.markdown("""
    <style>
    .stApp { background-color: #0b141a; }
    .stChatInputContainer > div { border-radius: 24px; background-color: #202c33 !important; color: white !important; border: 1px solid #2a3942; }
    [data-testid="stChatMessage"] { background-color: transparent !important; padding: 0 !important; margin-bottom: 1rem; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { flex-direction: row-reverse; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
        background-color: #005c4b !important; border-radius: 18px 18px 0px 18px !important; padding: 10px 14px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3); max-width: 75%; margin-left: auto; margin-right: 0;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { flex-direction: row; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] {
        background-color: #202c33 !important; border-radius: 0px 18px 18px 18px !important; padding: 10px 14px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.3); max-width: 75%; margin-right: auto; margin-left: 0;
    }
    [data-testid="stChatMessageContent"], [data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] div, 
    [data-testid="stChatMessageContent"] span, [data-testid="stChatMessageContent"] strong, [data-testid="stChatMessageContent"] li,
    [data-testid="stChatMessageContent"] table, [data-testid="stChatMessageContent"] th, [data-testid="stChatMessageContent"] td { color: #e9edef !important; }
    .chat-timestamp { font-size: 0.65rem; color: #8696a0; text-align: right; margin-top: 6px; display: block; }
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 { color: #e9edef !important; }
    [data-testid="stChatMessage"] [data-testid="stIconContainer"] { width: 30px; height: 30px; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

st.title("🩺 Healthcare Intelligence")

# --- Initialize Persistent Session States ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_id" not in st.session_state: st.session_state.user_id = None
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "view" not in st.session_state: st.session_state.view = "chat" # Used to toggle Chat vs Profile Editor

# --- PHASE 1: LOGIN TERMINAL ---
if not st.session_state.authenticated:
    st.subheader("🔐 Patient Portal Login")
    phone_input = st.text_input("Mobile Phone Number", placeholder="e.g., +917123456789").strip()
    
    if st.button("Verify Identity & Enter"):
        if phone_input:
            try:
                response = requests.get(f"{BACKEND_URL}/users/phone/{phone_input}")
                if response.status_code == 200:
                    data = response.json()
                    if data["exists"]:
                        st.session_state.user_id = data["user_id"]
                        st.session_state.user_name = data["name"]
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.warning("User not found. Please complete onboarding.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection Failure: Ensure your backend server is live.")

# --- PHASE 2: ACTIVE SYSTEM INTERFACE ---
elif st.session_state.authenticated:
    
    # ┌──────────────────────────────────────────────┐
    # │ DYNAMIC SIDEBAR
    # └──────────────────────────────────────────────┘
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"ID: {st.session_state.user_id}")
        st.divider()
        
        # Navigation
        if st.button("💬 Chat Interface", use_container_width=True):
            st.session_state.view = "chat"
            st.rerun()
        if st.button("📋 Edit Patient Profile", use_container_width=True):
            st.session_state.view = "profile"
            st.rerun()
            
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # ==========================================
    # VIEW: CHAT INTERFACE
    # ==========================================
    if st.session_state.view == "chat":
        
        # ✨ AUTO-WELCOME MESSAGE INJECTOR
        if not st.session_state.chat_history:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"Hello **{st.session_state.user_name}**! 👋 I am your secure clinical assistant. How can I help you today?",
                "timestamp": datetime.now().strftime("%I:%M %p")
            })

        status_bar = st.empty()
        chat_container = st.container(height=500, border=False)
        
        with chat_container:
            for bubble in st.session_state.chat_history:
                avatar_icon = "👤" if bubble["role"] == "user" else "🩺"
                with st.chat_message(bubble["role"], avatar=avatar_icon):
                    st.markdown(bubble["content"])
                    st.markdown(f"<span class='chat-timestamp'>{bubble.get('timestamp', '')}</span>", unsafe_allow_html=True)
                    
        prompt = st.chat_input("Type Message... ➤", accept_file=True, file_type=["jpg", "jpeg", "png", "pdf"])
        
        if prompt:
            current_time = datetime.now().strftime("%I:%M %p")
            user_text = prompt.text.strip()
            uploaded_file = prompt.files[0] if prompt.files else None
            
            display_text = user_text
            if uploaded_file and not user_text:
                display_text = f"📎 *Attached Document: {uploaded_file.name}*"
            elif uploaded_file:
                display_text = f"{user_text}\n\n📎 *Attached Document: {uploaded_file.name}*"
                
            st.session_state.chat_history.append({"role": "user", "content": display_text, "timestamp": current_time})
            
            with chat_container:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(display_text)
                    st.markdown(f"<span class='chat-timestamp'>{current_time}</span>", unsafe_allow_html=True)
                
            if uploaded_file:
                status_bar.info("👁️ Vision Agent analyzing uploaded document...")
            else:
                status_bar.info("🧠 Medical Agent Analyzing Symptoms...")
                
            api_message = user_text if user_text else "Please analyze this attached document."
            payload = {"user_id": st.session_state.user_id, "message": api_message}
            if uploaded_file:
                payload["image_base64"] = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
                
            try:
                chat_res = requests.post(f"{BACKEND_URL}/chat", json=payload, stream=True)
                if chat_res.status_code == 200:
                    with chat_container:
                        with st.chat_message("assistant", avatar="🩺"):
                            message_placeholder = st.empty()
                            full_response = ""
                            
                            def stream_parser(response):
                                try:
                                    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                                        if chunk: yield chunk if isinstance(chunk, str) else chunk.decode('utf-8')
                                except requests.exceptions.ChunkedEncodingError:
                                    yield "\n\n⚠️ *(Connection interrupted.)*"
                            
                            for chunk_text in stream_parser(chat_res):
                                full_response += chunk_text
                                message_placeholder.markdown(full_response + " ▌")
                                
                            bot_time = datetime.now().strftime("%I:%M %p")
                            message_placeholder.markdown(full_response + f"<span class='chat-timestamp'>{bot_time}</span>", unsafe_allow_html=True)
                            
                    status_bar.empty()
                    st.session_state.chat_history.append({"role": "assistant", "content": full_response, "timestamp": bot_time})
            except Exception as e:
                status_bar.error(f"❌ Connection Error: {e}")

    # ==========================================
    # VIEW: EDIT PROFILE 
    # ==========================================
    elif st.session_state.view == "profile":
        st.subheader("📋 Edit Patient Profile")
        st.caption("Update your clinical metrics so the AI can provide accurate personalized advice.")
        
        # Fetch current profile data
        res = requests.get(f"{BACKEND_URL}/users/profile/{st.session_state.user_id}")
        
        if res.status_code == 200:
            profile_data = res.json()
            
            with st.form("edit_profile_form"):
                col1, col2 = st.columns(2)
                
                # Helpers to safely grab indexes for selectboxes
                gender_opts = ["Male", "Female", "Other"]
                life_opts = ["Sedentary", "Moderate", "Active"]
                smoke_opts = ["No", "Yes"]
                
                with col1:
                    name = st.text_input("Full Legal Name", value=profile_data.get("name", ""))
                    age = st.number_input("Age Baseline", min_value=1, max_value=120, value=profile_data.get("age", 30))
                    gender = st.selectbox("Biological Sex Assignment", gender_opts, index=gender_opts.index(profile_data.get("gender", "Male")) if profile_data.get("gender") in gender_opts else 0)
                    location = st.text_input("Location (City)", value=profile_data.get("location", ""))
                with col2:
                    lifestyle = st.selectbox("Active Profile", life_opts, index=life_opts.index(profile_data.get("lifestyle_type", "Sedentary")) if profile_data.get("lifestyle_type") in life_opts else 0)
                    bmi = st.number_input("Calculated BMI Factor", min_value=10.0, max_value=50.0, value=float(profile_data.get("bmi", 22.5)), step=0.1)
                    smoking = st.selectbox("Tobacco Consumer?", smoke_opts, index=smoke_opts.index(profile_data.get("smoking_status", "No")) if profile_data.get("smoking_status") in smoke_opts else 0)
                    
                st.markdown("---")
                st.markdown("#### 🏥 Clinical History & Safety Profiles")
                
                conditions_input = st.text_input("Diagnosed Chronic Conditions (comma separated)", value=", ".join(profile_data.get("conditions", [])))
                meds_input = st.text_input("Active Prescribed Maintenance Medications (comma separated)", value=", ".join(profile_data.get("medications", [])))
                allergies_input = st.text_input("Known Drug or Environmental Allergies (comma separated)", value=", ".join(profile_data.get("allergies", [])))
                
                severity = "None"
                if conditions_input and conditions_input.strip().lower() != "none":
                    severity = st.selectbox("General Conditions Severity Index", ["Mild", "Medium", "High"])
                    
                submit_update = st.form_submit_button("💾 Save Profile Changes")
                
                if submit_update:
                    def parse_medical_list(text_string):
                        if not text_string or text_string.strip().lower() == "none": return []
                        return [item.strip() for item in text_string.split(",") if item.strip()]
                    
                    payload = {
                        "phone_number": profile_data.get("phone_number", ""), # Preserved for backend schema validation
                        "name": name, 
                        "age": age, 
                        "gender": gender,
                        "lifestyle_type": lifestyle, 
                        "bmi": bmi, 
                        "smoking_status": smoking,
                        "location": location.strip(),
                        "conditions": parse_medical_list(conditions_input),
                        "medications": parse_medical_list(meds_input),
                        "allergies": parse_medical_list(allergies_input),
                        "severity": severity
                    }
                    
                    update_res = requests.put(f"{BACKEND_URL}/users/profile/{st.session_state.user_id}", json=payload)
                    
                    if update_res.status_code == 200:
                        st.session_state.user_name = name
                        st.success("✅ Profile Updated Successfully!")
                        st.session_state.view = "chat"
                        st.rerun()
                    else:
                        st.error(f"Failed to update profile: {update_res.text}")
        else:
            st.error("⚠️ Could not load profile data from the server.")