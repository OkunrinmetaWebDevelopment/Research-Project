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
    


# Helper function (same as you provided, with minor improvements)
def answer_question_from_text(
    question: str,
    chunks: List[str],
    llm,
    include_sources: bool = True
) -> dict:
    """
    Answer a specific question using provided text chunks.
    """
    # Combine chunks into context with source labels
    context = "\n\n".join([
        f"[Source {i+1}]\n{chunk}" 
        for i, chunk in enumerate(chunks)
    ])
    
    # Create answering prompt
    prompt = f"""Based on the following context, answer the question below. 

Instructions:
- Provide a clear, accurate answer based ONLY on the given context
- If the answer is not in the context, say "I cannot answer this based on the provided information"
- Be concise but complete
- If citing specific information, mention which source it came from (e.g., "According to Source 2...")

Context:
{context}

Question: {question}

Answer:"""

    try:
        # Get LLM response
        response = llm.invoke(prompt)
        
        # Extract text from response
        if hasattr(response, 'content'):
            answer_text = response.content.strip()
        else:
            answer_text = str(response).strip()
        
        result = {"answer": answer_text}
        
        # Extract which sources were cited
        if include_sources:
            cited_sources = []
            for i in range(len(chunks)):
                if f"Source {i+1}" in answer_text:
                    cited_sources.append({
                        "source_id": i+1,
                        "text": chunks[i][:200] + "..." if len(chunks[i]) > 200 else chunks[i]
                    })
            result["sources"] = cited_sources
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error answering question: {str(e)}"
        )


# Example usage with multiple questions
def answer_multiple_questions(
    questions: List[str],
    chunks: List[str],
    llm
) -> List[dict]:
    """
    Answer multiple questions from the same context.
    More efficient than calling answer_question_from_text repeatedly.
    """
    context = "\n\n".join([
        f"[Source {i+1}]\n{chunk}" 
        for i, chunk in enumerate(chunks)
    ])
    
    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    
    prompt = f"""Based on the following context, answer each question below.

Context:
{context}

Questions:
{questions_text}

For each question, provide a clear answer based ONLY on the context. If information is not available, state that clearly.

Answers (format as "Q1: [answer]", "Q2: [answer]", etc.):"""

    try:
        response = llm.invoke(prompt)
        
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        # Parse answers
        answers = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q') and ':' in line:
                # Extract answer after the colon
                answer = line.split(':', 1)[1].strip()
                answers.append({"answer": answer})
        
        return answers[:len(questions)]  # Ensure we only return requested number
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error answering questions: {str(e)}"
        )



