import os
import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB client
# Using a persistent client to save the database to disk
client = chromadb.PersistentClient(path="./db/chroma_db")

# Use a default embedding function (Sentence Transformers)
# This will download a small model locally
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Get or create the collection
collection = client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=embedding_fn
)

def index_documents():
    """
    Reads text files from the docs/ directory and indexes them into ChromaDB.
    Should be run on startup or when docs change.
    """
    docs_dir = "docs"
    if not os.path.exists(docs_dir):
        print(f"Docs directory '{docs_dir}' not found.")
        return

    documents = []
    metadatas = []
    ids = []

    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Simple chunking by splitting on double newlines (paragraphs)
                # In a real app, use a smarter chunker (e.g., LangChain's RecursiveCharacterTextSplitter)
                chunks = content.split("\n\n")
                
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        documents.append(chunk)
                        metadatas.append({"source": filename})
                        ids.append(f"{filename}_{i}")

    if documents:
        print(f"Indexing {len(documents)} chunks from {len(set(m['source'] for m in metadatas))} files...")
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print("Indexing complete.")
    else:
        print("No documents found to index.")

def search_knowledge_base(query: str):
    """
    Searches the knowledge base for relevant documents.
    Use this tool when the user asks about policies, FAQs, or general information.
    """
    print(f"[Knowledge Search] Querying: '{query}'")
    
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    
    # Format results
    formatted_results = ""
    if results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            source = results["metadatas"][0][i]["source"]
            formatted_results += f"--- Source: {source} ---\n{doc}\n\n"
            
    return formatted_results or "No relevant information found in the knowledge base."

# Auto-index on import (for simplicity in this prototype)
# In production, this should be a separate build step or admin trigger
try:
    index_documents()
except Exception as e:
    print(f"Warning: Failed to index documents: {e}")
