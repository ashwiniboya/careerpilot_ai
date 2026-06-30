import os
import uuid
import re
from typing import List, Dict, Any, Optional
import numpy as np
from loguru import logger
import chromadb
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Simple vocabulary mapping for semantic matching in offline test environments
MOCK_VOCAB = {
    "python": 0,
    "react": 1,
    "docker": 2,
    "kubernetes": 3,
    "system": 4,
    "javascript": 5,
    "learning": 6,
    "ml": 7
}

class GeminiEmbedder:
    """Wrapper around Gemini SDK to generate text embeddings."""

    def __init__(self, model_name: str = "text-embedding-004"):
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_mock = not self.api_key or self.api_key.strip() == ""

        if self.use_mock:
            logger.warning("GEMINI_API_KEY not found in environment. Initializing RAG with Mock Embedder.")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai
                logger.info("Gemini Embedder initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini SDK, falling back to mock: {e}")
                self.use_mock = True

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding for a single text string."""
        if self.use_mock:
            # text-embedding-004 has 768 dimensions
            vector = [0.0] * 768
            
            # Extract words and check matches against vocab
            words = re.findall(r'\b\w+\b', text.lower())
            for w in words:
                if w in MOCK_VOCAB:
                    vector[MOCK_VOCAB[w]] = 10.0
                    
            # Add a small amount of random noise to ensure uniqueness and float variety
            np.random.seed(hash(text) % 2**32)
            noise = np.random.randn(768) * 0.05
            for i in range(768):
                vector[i] += noise[i]
                
            # Normalize vector to unit length
            norm = np.linalg.norm(vector)
            return (vector / norm).tolist() if norm > 0 else vector
        
        try:
            response = self.client.embed_content(
                model=f"models/{self.model_name}",
                content=text,
                task_type="retrieval_document"
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Gemini embedding API call failed: {e}. Falling back to mock vector.")
            np.random.seed(hash(text) % 2**32)
            vector = np.random.randn(768).tolist()
            norm = np.linalg.norm(vector)
            return (vector / norm).tolist() if norm > 0 else vector

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for multiple texts."""
        return [self.get_embedding(t) for t in texts]


class VectorStore:
    """Interface to manage the ChromaDB local vector database."""

    def __init__(self, db_path: str = "vector_db", collection_name: str = "careerpilot_rag"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize chroma client
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = GeminiEmbedder()
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )
        logger.info(f"ChromaDB local vector store initialized at {db_path}.")

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: Optional[List[str]] = None):
        """Indexes documents in ChromaDB with embeddings."""
        if not texts:
            return

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        # Ensure metadata values are compatible with Chroma (string, int, float, bool)
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            clean_metadatas.append(clean_meta)

        embeddings = self.embedder.get_embeddings(texts)
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=clean_metadatas,
            ids=ids
        )
        logger.info(f"Indexed {len(texts)} chunks in vector database.")

    def search(self, query: str, user_id: int, limit: int = 5, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries the vector store for similar documents filtering by user_id and optionally doc_type."""
        query_embedding = self.embedder.get_embedding(query)
        
        # Build filter using Chroma's operator format for multiple conditions
        if doc_type:
            where_filter = {
                "$and": [
                    {"user_id": user_id},
                    {"doc_type": doc_type}
                ]
            }
        else:
            where_filter = {"user_id": user_id}

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )
            
            # Format outputs
            formatted_results = []
            if results and 'documents' in results and results['documents']:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else [{}] * len(documents)
                distances = results['distances'][0] if 'distances' in results and results['distances'] else [0.0] * len(documents)
                ids = results['ids'][0] if 'ids' in results else [""] * len(documents)

                for doc, meta, dist, id_val in zip(documents, metadatas, distances, ids):
                    formatted_results.append({
                        "id": id_val,
                        "text": doc,
                        "metadata": meta,
                        "score": 1.0 - float(dist)  # Convert distance to a similarity score approximation
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []

    def delete_user_documents(self, user_id: int):
        """Deletes all indexed vectors associated with a user."""
        try:
            self.collection.delete(where={"user_id": user_id})
            logger.info(f"Deleted vector database entries for user {user_id}.")
        except Exception as e:
            logger.error(f"Failed to delete documents for user {user_id}: {e}")
