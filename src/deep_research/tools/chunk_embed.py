from __future__ import annotations
import math
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from db.models import SourceEmbedding


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


async def embed_texts_ollama(texts: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
    """Call Ollama embeddings endpoint. Returns list of 768-dim vectors."""
    import httpx
    embeddings = []
    async with httpx.AsyncClient(timeout=30) as client:
        for text in texts:
            r = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": model, "prompt": text},
            )
            r.raise_for_status()
            embeddings.append(r.json()["embedding"])
    return embeddings


async def chunk_embed_and_store(
    session: AsyncSession,
    job_id: str,
    source_id: str,
    text: str,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
) -> int:
    """Chunk text, embed via Ollama, insert into source_embedding. Returns chunk count."""
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        return 0
    vectors = await embed_texts_ollama(chunks)
    rows = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        rows.append({
            "job_id": job_id, "source_id": source_id,
            "chunk_index": i, "chunk_text": chunk, "embedding": vec,
        })
    stmt = insert(SourceEmbedding).values(rows).on_conflict_do_nothing(
        index_elements=["source_id", "chunk_index"]
    )
    await session.execute(stmt)
    return len(chunks)
