import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
import numpy as np
from fastembed import TextEmbedding
import faiss


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks based on approximate token count.
    Using simple word-based splitting as approximation.
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
        
        i += chunk_size - overlap
        
        if i >= len(words):
            break
    
    return chunks if chunks else [text]


def create_embeddings(texts: List[str], model: TextEmbedding) -> np.ndarray:
    """
    Generate embeddings for a list of texts using FastEmbed.
    """
    embeddings_generator = model.embed(texts)
    embeddings = list(embeddings_generator)
    return np.array(embeddings, dtype=np.float32)


def create_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """
    Create an in-memory FAISS index for similarity search using inner product (cosine similarity).
    """
    dimension = int(embeddings.shape[1])
    
    faiss.normalize_L2(embeddings)
    
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    return index


def retrieve_relevant_chunks(
    query: str,
    chunks: List[str],
    index,
    embedding_model: TextEmbedding,
    top_k: int = 3
) -> List[str]:
    """
    Retrieve the most relevant chunks for a given query.
    """
    query_embedding = np.array(list(embedding_model.embed([query])), dtype=np.float32)
    
    faiss.normalize_L2(query_embedding)
    
    k = min(top_k, index.ntotal)
    distances, indices = index.search(query_embedding, k)
    
    relevant_chunks = [chunks[idx] for idx in indices[0] if idx < len(chunks)]
    
    return relevant_chunks


def generate_questions_from_chunks(
    chunks: List[str],
    llm,
    num_questions: int = 5
) -> List[str]:
    """
    Generate questions from retrieved chunks using an LLM.
    """
    context = "\n\n".join([f"Chunk {i+1}: {chunk}" for i, chunk in enumerate(chunks)])
    
    prompt = f"""Based on the following text content, generate {num_questions} diverse, specific, and insightful questions that someone might ask about this content. 

The questions should:
- Be clear and directly answerable from the given context
- Cover different aspects or topics within the text
- Range from factual to analytical
- Be phrased naturally as if asked by a curious reader

Context:
{context}

Generate exactly {num_questions} questions, one per line, without numbering or bullet points:"""

    try:
        response = llm.invoke(prompt)
        
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        questions = [
            line.strip().lstrip('0123456789.-) ').strip()
            for line in response_text.strip().split('\n')
            if line.strip() and '?' in line
        ]
        
        questions = [q for q in questions if len(q) > 10][:num_questions]
        
        return questions
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")



