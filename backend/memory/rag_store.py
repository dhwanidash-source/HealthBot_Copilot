import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

RAG_INDEX_PATH = "./guidelines_faiss_index"

class RAGKnowledgeBase:
    def __init__(self):
        # We use the same fast, local embedding model
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = self._load_index()

    def _load_index(self):
        """Loads the NHS FAISS index if it exists. Returns None if it hasn't been built yet."""
        if os.path.exists(RAG_INDEX_PATH):
            print("Loading Knowledge Base...")
            return FAISS.load_local(
                RAG_INDEX_PATH, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        return None

    def search_guidelines(self, query: str, k: int = 2) -> str:
        """
        Searches the guidelines and extracts the filename and exact page number.
        """
        if not self.vector_store:
            return "Error: RAG database not initialized."
            
        results = self.vector_store.similarity_search(query, k=k)
        
        context_chunks = []
        for res in results:
            # Extract file path and page number
            source_path = res.metadata.get("source", "Unknown Document")
            page_num = res.metadata.get("page", 0) + 1 
            
            # Get just the filename (e.g., "guidelines_2026.pdf")
            filename = os.path.basename(source_path)
            
            # Format the chunk with explicit Document and Page metadata
            chunk_text = f"--- Document: {filename} | Page: {page_num} ---\n{res.page_content}"
            context_chunks.append(chunk_text)
            
        return "\n\n".join(context_chunks)

# Global instance to be used by the Patient Agent
rag_db = RAGKnowledgeBase()