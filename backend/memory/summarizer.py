# backend/memory/summarizer.py
from core.llm import llm  
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate

def compress_chat_history(messages: list[BaseMessage]) -> str:
    """
    Takes a list of LangGraph messages and compresses them into a dense summary 
    using your centralized Groq model instance.
    """
    # Extract just the text from the LangGraph message objects
    dialogue_text = "\n".join(
        [f"{m.type}: {m.content}" for m in messages if isinstance(m.content, str)]
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Memory Compressor for a Healthcare AI.
        Extract the following from the conversation log:
        1. Explicitly stated health symptoms or conditions.
        2. Interest in specific services or campaigns.
        3. General behavioral sentiment (e.g., anxious, proactive).
        
        Keep it highly dense and factual. Do not use filler words."""),
        ("user", "Conversation Log:\n{dialogue}")
    ])
    
    # Pipe the prompt directly into your existing Groq LLM
    chain = prompt | llm
    
    # Invoke the model
    response = chain.invoke({"dialogue": dialogue_text})
    
    return response.content