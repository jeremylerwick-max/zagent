-- V002__embedding.sql
-- NOTE: Using 768 dimensions for nomic-embed-text (not 1536)
BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS source_embedding (
  embedding_id BIGSERIAL PRIMARY KEY,
  job_id       UUID NOT NULL REFERENCES research_job(job_id) ON DELETE CASCADE,
  source_id    TEXT NOT NULL REFERENCES source_document(source_id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  chunk_index  INTEGER NOT NULL,
  chunk_text   TEXT NOT NULL,
  embedding    vector(768) NOT NULL  -- nomic-embed-text = 768 dim
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_source_embedding_chunk
ON source_embedding (source_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_source_embedding_cosine
ON source_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMIT;
