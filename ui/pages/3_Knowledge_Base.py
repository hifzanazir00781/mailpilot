# File: ui/pages/3_Knowledge_Base.py

import streamlit as st
import os
import sys
from pypdf import PdfReader

# Root directory ko system path mein add karna taake backend import ho sakay
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.vector_store import get_tenant_collection, get_embedding_model

# Security Check: Agar user logged in nahi hai toh rok dein
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("🔒 Please log in from the main application first.")
    st.stop()

# Context se tenant_id nikalna (Row-Level Security)
tenant_id = st.session_state.user_data['tenant_id']

st.title("📚 Knowledge Base Management")
st.markdown("Upload documents (PDF, TXT) to empower your AI support system with searchable context.")

# Get Chroma collection and Gemini embedding model for this specific tenant
collection = get_tenant_collection(tenant_id)
embedding_model = get_embedding_model()

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """
    Text ko specified chunk size aur overlap ke sath split karta hai.
    """
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def extract_text_from_file(uploaded_file) -> str:
    """
    Uploaded file (PDF ya TXT) se text extract karta hai.
    """
    text = ""
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    elif uploaded_file.type == "text/plain":
        text = uploaded_file.getvalue().decode("utf-8")
    return text

# --- UPLOAD SECTION ---
st.markdown("### 📤 Upload New Documents")
uploaded_files = st.file_uploader(
    "Choose PDF or TXT files", 
    type=["pdf", "txt"], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Process & Store Documents", type="primary"):
        with st.spinner("Processing documents, generating embeddings, and storing in ChromaDB..."):
            for uploaded_file in uploaded_files:
                filename = uploaded_file.name
                raw_text = extract_text_from_file(uploaded_file)
                
                if not raw_text.strip():
                    st.warning(f"⚠️ File '{filename}' appears to be empty or unreadable.")
                    continue
                    
                # Chunking text into ~800 char blocks with 100 char overlap
                chunks = chunk_text(raw_text, chunk_size=800, overlap=100)
                
                if not chunks:
                    continue
                    
                # Generate embeddings using Gemini embedding model
                embeddings = embedding_model.embed_documents(chunks)
                
                # Create unique IDs and metadatas for each chunk
                ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
                metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]
                
                # Add to tenant-isolated ChromaDB collection
                collection.add(
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
            
            st.success("✅ All documents successfully processed and embedded!")
            st.rerun()

st.markdown("---")

# --- DOCUMENT LIST & MANAGEMENT SECTION ---
st.markdown("### 🗂️ Uploaded Knowledge Base Documents")

try:
    # Fetch all metadata from ChromaDB collection to list uploaded documents
    data = collection.get(include=['metadatas'])
    metadatas = data.get('metadatas', [])
    
    # Aggregate chunk counts by source filename
    doc_counts = {}
    for meta in metadatas:
        if meta and 'source' in meta:
            src = meta['source']
            doc_counts[src] = doc_counts.get(src, 0) + 1
            
    if not doc_counts:
        st.info("No documents uploaded yet. Upload some files above to build your knowledge base!")
    else:
        # Table header
        col1, col2, col3 = st.columns([3, 1.5, 1])
        col1.markdown("**Document Name**")
        col2.markdown("**Chunks Count**")
        col3.markdown("**Action**")
        st.markdown("---")
        
        for filename, count in doc_counts.items():
            r_col1, r_col2, r_col3 = st.columns([3, 1.5, 1])
            r_col1.write(f"📄 `{filename}`")
            r_col2.write(f"{count} chunks")
            
            with r_col3:
                if st.button("Delete 🗑️", key=f"del_{filename}"):
                    # Delete all chunks matching this source file from ChromaDB
                    collection.delete(where={"source": filename})
                    st.success(f"Deleted '{filename}' successfully!")
                    st.rerun()
                    
except Exception as e:
    st.error(f"Error loading documents from vector store: {str(e)}")