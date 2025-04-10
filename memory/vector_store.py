# memory/vector_store.py
import ollama
import numpy as np

class VectorStore:
    def __init__(self):
        self.embeddings = {}
        self.model = "distilbert"  # Using DistilBERT for embeddings
    
    def get_embedding(self, text):
        """Get embedding for a text string"""
        if text in self.embeddings:
            return self.embeddings[text]
        
        # In a real implementation, we'd use a proper embedding model
        # For hackathon purposes, we'll use a simplified approach
        
        # Use Ollama to generate embeddings
        # Note: This is a simplified approach - in production we'd use a dedicated embedding model
        response = ollama.embeddings(
            model=self.model,
            prompt=text
        )
        
        embedding = response.get('embedding', [])
        
        # Cache the embedding
        self.embeddings[text] = embedding
        
        return embedding
    
    def find_similar(self, query, candidates, top_n=5):
        """Find most similar texts to a query from a list of candidates"""
        if not candidates:
            return []
        
        query_embedding = self.get_embedding(query)
        
        similarities = []
        for candidate in candidates:
            candidate_embedding = self.get_embedding(candidate)
            similarity = self._cosine_similarity(query_embedding, candidate_embedding)
            similarities.append((candidate, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return similarities[:top_n]
    
    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors"""
        # Convert to numpy arrays for easier calculation
        a = np.array(a)
        b = np.array(b)
        
        # Calculate cosine similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return dot_product / (norm_a * norm_b)
