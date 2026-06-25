from memory.faiss_store import vector_db
import json

def vector_search(user_id: str, query: str) -> str:
    """
    Searches FAISS similarity index for past chat summaries and behavioral context.
    """
    try:
        memories = vector_db.recall_memories(user_id=user_id, query=query)
        if not memories:
            return json.dumps({"message": "No relevant past conversations found."})
        
        return json.dumps({"past_context": memories})
    except Exception as e:
        return json.dumps({"error": str(e)})