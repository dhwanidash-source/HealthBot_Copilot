# ingest.py
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# 1. Get the directory where ingest.py lives (the 'scripts' folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data"))

# 3. Save the FAISS index up in the 'backend' folder so your app can find it
RAG_INDEX_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "guidelines_faiss_index"))

def ingest_documents():
    print(f"Looking for PDFs exactly here: {DATA_DIR}...")
    
    # Use the dedicated PDF loader
    loader = PyPDFDirectoryLoader(DATA_DIR)
    documents = loader.load()
    
    if not documents:
        print(f"❌ No PDFs found! Please put your PDF file into the '{DATA_DIR}' folder.")
        return

    # Chunk the documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    print(f" Created {len(chunks)} chunks from {len(documents)} pages.")

    # Generate Embeddings and Save to FAISS
    print("🧠 Generating vector embeddings (this might take a minute)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(RAG_INDEX_PATH)
    
    print(f"✅ RAG Knowledge Base successfully saved to {RAG_INDEX_PATH}!")

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    ingest_documents()