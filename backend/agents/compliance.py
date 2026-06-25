# backend/agents/compliance.py
import re
from langchain_core.messages import AIMessage, SystemMessage
from core.state import AgentState
from core.llm import llm, get_text_only_history
from core.utils import universal_tag_cleaner

async def compliance_agent_node(state: AgentState):
    """
    Universal Compliance, Formatting, and Proactive Dialogue Agent Node.
    100% Single-Pass LLM. Extremely fast, dynamic, and prevents data repetition.
    """
    messages = state.get("messages", [])
   
    safe_messages = get_text_only_history(messages)
    
    last_user_msg = ""
    last_assistant_msg = ""
    raw_system_data = ""
    
    # 1. BULLETPROOF EXTRACTION LOGIC
    if safe_messages and safe_messages[-1].type == "ai":
        raw_system_data = str(safe_messages[-1].content)
        
    last_human_idx = -1
    for i in range(len(safe_messages) - 1, -1, -1):
        if safe_messages[i].type == "human":
            last_user_msg = str(safe_messages[i].content).strip()
            last_human_idx = i
            break
            
    if last_human_idx > 0:
        for i in range(last_human_idx - 1, -1, -1):
            if safe_messages[i].type == "ai":
                last_assistant_msg = str(safe_messages[i].content).strip()
                break

    # 2. CASUAL GREETING & GOODBYE SHORT-CIRCUIT
    last_user_msg_clean = re.sub(r'[^\w\s]', '', last_user_msg.lower()).strip()
    casual_phrases = [
        "hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", 
        "bye", "goodbye", "thanks", "thank you", "see ya", "take care", "ok", "okay", "alright"
    ]
    
    is_casual = last_user_msg_clean in casual_phrases or (
        len(last_user_msg_clean.split()) <= 3 and any(word in last_user_msg_clean.split() for word in casual_phrases)
    )

    if is_casual:
        print("👋 [Compliance Agent] Casual greeting/farewell detected. Sending minimalist response.")
        greeting_prompt = [
            SystemMessage(content="You are a warm, professional clinical assistant portal. The user just said a simple greeting, goodbye, or thank you. Reply with a short, warm sentence acknowledging them (e.g., greeting them back or wishing them well). DO NOT include tables, health tips, next steps, or a medical disclaimer for this basic interaction."),
        ] + safe_messages[:last_human_idx + 1]
        response = await llm.ainvoke(greeting_prompt)
        return {"messages": [AIMessage(content=str(response.content))], "sender": "ComplianceAgent"}

    # 3. HISTORY SLICING
    clean_history = safe_messages[:last_human_idx + 1] if last_human_idx != -1 else safe_messages

    # 4. THE UNIVERSAL FORMATTING ENGINE
    formatting_prompt = SystemMessage(content=f"""
    You are the Conversational AI Interface and Chief Patient Safety Officer.
    
    USER'S CURRENT MESSAGE: "{last_user_msg}"
    PREVIOUS ASSISTANT QUESTION: "{last_assistant_msg}"
    
    RAW SYSTEM DATA (From Specialist Agent):
    {raw_system_data}
    
    YOUR MISSION: 
    Act as a dynamic translation layer. Read ONLY the bracketed tags present in the RAW SYSTEM DATA and assemble them into a beautiful, empathetic conversational response.
    
    UNIVERSAL FORMATTING RULES & VISUAL HIERARCHY:
    
    1. 🗣️ TONE & READABILITY (CRITICAL):
       - Do NOT repeat the same introductory robotic phrases (e.g., "I'm here to help you with...") if you already said them in the PREVIOUS ASSISTANT QUESTION.
       - The output MUST look beautiful and be easy to read. Use clean bullet points, bolded keywords, and short 1-to-2 sentence paragraphs. Jump straight into the empathetic response.
       - After EVERY major section below, insert a blank line followed by a markdown horizontal rule `---` and another blank line before the next section. This creates clear visual separation between sections.
       
    2. 🛡️ SAFETY & INTENT GATE:
       - If the USER'S CURRENT MESSAGE is offensive or completely unrelated non-medical chatter: 
         - Ignore the RAW SYSTEM DATA entirely.
         - Write a polite, warm 2-sentence reminder that you handle healthcare triage and directory services only.
         - Naturally re-ask the PREVIOUS ASSISTANT QUESTION at the end.
         - Stop here. Output ONLY this text.
       
    3. 🩺 MAIN CLINICAL DIAGNOSIS (If present in RAW DATA):
       - `[CLINICAL_DIAGNOSIS]`: Present it as a warm, professional summary. Do NOT use "CLINICAL_DIAGNOSIS" as a header.
         - Break the text into highly scannable bullet points and short 1-to-2 sentence paragraphs. 
         - 📝 DOCUMENT FORMATTING: If the summary contains lab results, blood work, or a medication list, you MUST structure that data visually using Markdown Tables or clean bolded lists.
       - After this section, insert a blank line, then `---`, then another blank line.
       
    4. 📚 CITATIONS (IMMEDIATELY AFTER DIAGNOSIS):
       - `**📚 Source Context:**`: ONLY if this exact text is present in the RAW DATA, you MUST append it cleanly DIRECTLY BELOW the clinical diagnosis. Do not place it at the very bottom of the chat.
       - After this section, insert a blank line, then `---`, then another blank line.
       
    5. 🧬 PERSONALIZATION & PROFILE (AFTER CITATIONS):
       - `[PATIENT_PROFILE_USED]`: Display this data transparently as a bulleted list below the citations, introduced with a short bolded label like "**Your Profile:**".
       - 🛑 MANDATORY PARAGRAPH BREAK: After the profile bullets, insert a blank line (do NOT use a `---` divider here — just whitespace). Then start the insights as a NEW, SEPARATE paragraph introduced with its own short bolded label like "**Personalized Insights:**". The profile bullets and the insight bullets are TWO DISTINCT bullet lists — never merge them into a single continuous list with no break.
       - `[PERSONALIZATION_INSIGHT]`: Format these tips as a clean, bulleted list below the profile, as its own separate paragraph per the rule above.
       - `[CONTRAINDICATION_WARNING]`: If present, display it prominently in bold.
       - After this section, insert a blank line, then `---`, then another blank line.
       
    6. 🏥 WEB SCRAPING & CLINICS (If present in RAW DATA):
       - `[CLINIC_RESULTS]:` You MUST explicitly output these clinics exactly as they are formatted. Introduce them warmly.
       - After this section, insert a blank line, then `---`, then another blank line.
       
    7. 🚪 CONVERSATIONAL GATE (If present in RAW DATA):
       - `[NEXT_QUESTION: <text>]` or `[MISSING_INFO: <text>]`: You MUST extract the actual <text> inside the brackets only and print it clearly on a new line.
       - After this section, insert a blank line, then `---`, then another blank line.
       
    8. 🚫 THE DE-TAGGING RULE:
       - You must NEVER print the literal brackets/tags to the user screen. Extract the human-readable text from them.
       
    9. ⚠️ DYNAMIC MEDICAL DISCLAIMER (CRITICAL ANTI-BOILERPLATE RULE):
       - ALWAYS append a medical disclaimer as the ABSOLUTE LAST element of your response, after all other sections and their dividers.
       - It MUST be on its own line, preceded by a blank line (do NOT add another `---` divider before it — the blank line is sufficient separation).
       - It MUST start exactly with "⚠️ Disclaimer: " followed by your custom text.
       - FORMATTING RULE: Do NOT use blockquotes (>), extra emojis, or bolded "Important" labels.
       - EXCEPTION: If the user's message is exclusively a polite greeting, thank you, or goodbye, DO NOT include the disclaimer.
       - 🛑 FORBIDDEN PHRASES: You are STRICTLY FORBIDDEN from using the phrases "substitute for professional medical advice", "general guidance", "consult a healthcare professional", or "seek medical attention".
       - YOUR TASK: Read the RAW SYSTEM DATA and the USER'S CURRENT MESSAGE. Write a 100% unique, highly specific 1-sentence warning based strictly on the exact condition, symptoms, or specialist mentioned in this specific turn.
    """)
    
    print("🛡️ [Compliance Agent] Processing through Universal Formatting Engine...")
    
    response = await llm.ainvoke([formatting_prompt] + clean_history)

    # 5. THE TARGETED TAG ANNIHILATOR (Python Safety Net)
    final_output = str(response.content)
    
    system_tags = [
        "NEXT_QUESTION", "MISSING_INFO", "CLINICAL_DIAGNOSIS", 
        "PERSONALIZATION_INSIGHT", "PATIENT_PROFILE_USED", 
        "CONTRAINDICATION_WARNING", "CLINIC_RESULTS", "SEVERITY", "SPECIALIST"
    ]
    
    for tag in system_tags:
        final_output = re.sub(rf'\[{tag}:\s*([\s\S]*?)\]', r'\1', final_output, flags=re.IGNORECASE)
        final_output = re.sub(rf'\[?\**{tag}\**\]?:\s*', '', final_output, flags=re.IGNORECASE)
        final_output = re.sub(rf'\[?\**{tag}\**\]?', '', final_output, flags=re.IGNORECASE)

    final_output = re.sub(r'\n{4,}', '\n\n\n', final_output)
    final_output = re.sub(r'(?<!\n\n)(⚠️ Disclaimer:)', r'\n\n⚠️ Disclaimer:', final_output)


    if "[CLINIC_RESULTS]" in raw_system_data:
        final_output = final_output.strip() + "\n[CLINIC_RESULTS_SHOWN]"

    return {
        "messages": [AIMessage(content=final_output.strip())],
        "sender": "ComplianceAgent"
    }