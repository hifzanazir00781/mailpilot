# File: agents/rag_agent.py

import os
import sys
import time
from typing import List, Dict, Any

# Root directory ko system path mein add karna
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.vector_store import get_tenant_collection
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def retrieve_relevant_context(query: str, tenant_id: int, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves relevant context chunks from the tenant-specific ChromaDB collection 
    using Gemini embeddings (gemini-embedding-001) with exponential backoff retry logic.
    """
    try:
        collection = get_tenant_collection(tenant_id)
    except Exception as e:
        print(f"❌ Error getting Chroma collection for tenant {tenant_id}: {str(e)}")
        return []

    try:
        count = collection.count()
        if count == 0:
            print(f"ℹ️ Knowledge base collection for tenant {tenant_id} is empty.")
            return []
    except Exception as e:
        print(f"⚠️ Error checking collection count: {str(e)}")

    try:
        embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
    except Exception as e:
        print(f"❌ Error initializing embedding model: {str(e)}")
        return []

    backoff_delays = [2, 4, 8]
    query_embedding = None

    for attempt, delay in enumerate(backoff_delays + [0]):
        try:
            print(f"🔍 [RAG Agent] Generating query embedding... (Attempt {attempt + 1})")
            query_embedding = embedding_model.embed_query(query)
            break
        except Exception as e:
            error_str = str(e)
            print(f"❌ Embedding error on attempt {attempt + 1}: {error_str}")
            if "503" in error_str or "Unavailable" in error_str or "429" in error_str or "ResourceExhausted" in error_str:
                if delay > 0:
                    print(f"⚠️ API Limit/Unavailable. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("❌ Failed to generate embedding after 3 retries.")
                    return []
            else:
                return []

    if not query_embedding:
        return []

    try:
        actual_k = min(top_k, count if 'count' in locals() and count > 0 else top_k)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k
        )
    except Exception as e:
        print(f"❌ Error querying ChromaDB collection: {str(e)}")
        return []

    retrieved_chunks = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for doc, meta in zip(documents, metadatas):
        retrieved_chunks.append({
            "content": doc,
            "source": meta.get("source", "Unknown"),
            "chunk_index": meta.get("chunk_index", 0)
        })

    print(f"✅ Retrieved {len(retrieved_chunks)} relevant context chunks from knowledge base.")
    return retrieved_chunks

# Test Block
if __name__ == "__main__":
    print("Testing RAG Agent Retrieval...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ ERROR: GEMINI_API_KEY not found! Please create a .env file and add your key.")
        sys.exit(1)
        
    test_tenant_id = 1
    test_query = "What is the refund policy?"
    
    print(f"\n--- Testing query for Tenant #{test_tenant_id} ---")
    print(f"Query: '{test_query}'")
    
    chunks = retrieve_relevant_context(test_query, test_tenant_id, top_k=3)
    
    print(f"\n--- Retrieved Results ({len(chunks)} chunks) ---")
    for idx, chunk in enumerate(chunks, 1):
        print(f"\n[Chunk {idx}]")
        print(f"Source: {chunk['source']} (Index: {chunk['chunk_index']})")
        print(f"Content: {chunk['content'][:200]}...")