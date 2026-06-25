# backend/memory/episodic_memory.py
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

FAISS_MEMORY_PATH = "./faiss_index_memory"

class EpisodicMemoryManager: 
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = self._load_or_create_index()

    def _load_or_create_index(self):
        if os.path.exists(FAISS_MEMORY_PATH):
            print("[Episodic Memory] Loading existing patient chat histories...")
            return FAISS.load_local(
                FAISS_MEMORY_PATH, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        else:
            print("✨ [Episodic Memory] Initializing fresh FAISS memory store...")
            # FAISS needs at least one document to define its vector shape
            empty_doc = Document(page_content="memory system initialized", metadata={"user_id": "system"})
            vs = FAISS.from_documents([empty_doc], self.embeddings)
            vs.save_local(FAISS_MEMORY_PATH)
            return vs

    def add_memory(self, user_id: str, session_id: str, summary: str):
        """Saves a summary of a conversation to the patient's private vector space."""
        doc = Document(
            page_content=summary,
            metadata={
                "user_id": user_id,       # Critical for privacy filtering!
                "session_id": session_id,
                "type": "chat_summary"
            }
        )
        self.vector_store.add_documents([doc])
        self.vector_store.save_local(FAISS_MEMORY_PATH)
        print(f"💾 [Episodic Memory] Chat summary saved for patient: {user_id}")

    def recall_memories(self, user_id: str, query: str, k: int = 2) -> list[str]:
        """Recalls past conversation summaries mathematically similar to the current query."""
        try:
            results = self.vector_store.similarity_search(
                query, 
                k=k, 
                filter={"user_id": user_id} # Ensures we only fetch THIS user's data
            )
            return [res.page_content for res in results]
        except Exception as e:
            print(f"⚠️ [Episodic Memory] Recall error: {e}")
            return []

# Instantiate globally so the backend can easily import it
episodic_db = EpisodicMemoryManager()