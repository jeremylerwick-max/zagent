from typing import List

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using nomic-embed-text via Ollama.
    Returns list of 768-dim vectors.
    """
    # TODO: wire to Ollama embeddings endpoint
    # curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"text"}'
    raise NotImplementedError
