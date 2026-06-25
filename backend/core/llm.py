import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage


load_dotenv()


if not os.getenv("GROQ_API_KEY"):
    raise ValueError("CRITICAL ERROR: GROQ_API_KEY is missing from your .env file.")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2
)


vision_llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.1
)


def get_text_only_history(messages: list) -> list:
    """
    UNIVERSAL SANITIZER: 
    Strips image dictionaries out of the chat history so Text-Only LLMs don't crash 
    when trying to read previous turns.
    """
    text_only_messages = []
    for msg in messages:
        if isinstance(msg.content, list):
            # Extract ONLY the text portion, stripping out the base64 image dict
            text_val = next((p["text"] for p in msg.content if p.get("type") == "text"), "")
            text_only_messages.append(
                HumanMessage(content=text_val) if msg.type == "human" else AIMessage(content=text_val)
            )
        else:
            text_only_messages.append(msg)
            
    return text_only_messages