# File: backend/vector_store.py

import os
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Ensure API key is present
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY is not set in the environment variables.")

def get_embedding_model():
    """
    Initializes and returns Google's Gemini embedding model via LangChain.
    """
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

def get_chroma_client():
    """
    Initializes a persistent ChromaDB client stored locally in a 'chroma_db' directory.
    Multi-tenant isolation can be handled via separate collections per tenant_id.
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
    os.makedirs(db_path, exist_ok=True)
    
    client = chromadb.PersistentClient(path=db_path)
    return client

def get_tenant_collection(tenant_id: int):
    """
    Retrieves or creates a dedicated ChromaDB collection for a specific tenant 
    to ensure strict data privacy and vector isolation.
    """
    client = get_chroma_client()
    embedding_model = get_embedding_model()
    
    collection_name = f"tenant_{tenant_id}_kb"
    
    # ChromaDB collection creation
    collection = client.get_or_create_collection(name=collection_name)
    return collection