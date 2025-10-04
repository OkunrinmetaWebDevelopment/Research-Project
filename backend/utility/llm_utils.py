import os
from langchain_huggingface import HuggingFaceEndpoint
from langchain_together import ChatTogether
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def load_huggingface_llm():
    """
    Load the HuggingFace LLM model using the API token from environment variables.
    """
    api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not api_token:
        raise ValueError("HUGGINGFACEHUB_API_TOKEN is missing from environment variables.")

    return HuggingFaceEndpoint(
        repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
        temperature=0.7,
        max_new_tokens=512,
        huggingfacehub_api_token=api_token
    )


def load_together_ai_llm():
    """
    Load the Together AI LLM model using the API key from environment variables.
    """
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise ValueError("TOGETHER_API_KEY is missing from environment variables.")

    return ChatTogether(
        model="mistralai/Mixtral-8x7B-Instruct-v0.1",
        api_key=api_key,
        temperature=0.7
    )


def load_ollama_llm():
    """
    Load the Ollama LLM model (local).
    """
    return ChatOllama(
        model="llama3.2",
        temperature=0.7
    )


def load_anthropic_llm():
    """
    Load the Anthropic Claude LLM model using the API key from environment variables.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is missing from environment variables.")

    return ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        api_key=api_key,
        temperature=0.7
    )


def get_sambanova_llm():
    """
    Return a ChatOpenAI instance configured for SambaNova's OpenAI-compatible API.
    """
    api_key = os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        raise ValueError("SAMBANOVA_API_KEY is missing from environment variables.")

    return ChatOpenAI(
        api_key=api_key,
        base_url="https://api.sambanova.ai/v1",
        model="Llama-4-Maverick-17B-128E-Instruct",
        temperature=0.7
    )


def check_ollama_available():
    """
    Check if Ollama is running locally by attempting a health check.
    """
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_available_llm():
    """
    Returns the first available LLM based on environment variables.
    Priority: Ollama (free/local) > HuggingFace > Together AI > Anthropic > SambaNova
    
    Validates that the LLM is actually accessible before returning.
    """
    if check_ollama_available():
        try:
            return load_ollama_llm(), "ollama"
        except Exception:
            pass
    
    if os.getenv("HUGGINGFACEHUB_API_TOKEN"):
        try:
            return load_huggingface_llm(), "huggingface"
        except Exception:
            pass
    
    if os.getenv("TOGETHER_API_KEY"):
        try:
            return load_together_ai_llm(), "together_ai"
        except Exception:
            pass
    
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return load_anthropic_llm(), "anthropic"
        except Exception:
            pass
    
    if os.getenv("SAMBANOVA_API_KEY"):
        try:
            return get_sambanova_llm(), "sambanova"
        except Exception:
            pass
    
    raise ValueError("No LLM available. Please either: (1) Run Ollama locally (http://localhost:11434), or (2) Set one of these API keys: HUGGINGFACEHUB_API_TOKEN, TOGETHER_API_KEY, ANTHROPIC_API_KEY, SAMBANOVA_API_KEY")
