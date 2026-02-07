-- V002: Add pgvector for semantic search
-- Enables similarity search across evidence and claims

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to evidence_ledger
-- Using 1536 dimensions (compatible with OpenAI ada-002, nomic-embed-text, etc.)
ALTER TABLE evidence_ledger
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Add embedding column to claims for semantic claim matching
ALTER TABLE claims
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Add content storage for full-text search (optional, for hybrid search)
ALTER TABLE evidence_ledger
ADD COLUMN IF NOT EXISTS content_text TEXT;

-- IVFFlat index for approximate nearest neighbor search
-- Good for datasets up to ~1M vectors
CREATE INDEX IF NOT EXISTS idx_evidence_embedding
ON evidence_ledger
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_claims_embedding
ON claims
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Full-text search index (for hybrid search)
CREATE INDEX IF NOT EXISTS idx_evidence_content_fts
ON evidence_ledger
USING gin (to_tsvector('english', COALESCE(content_text, '')));

-- Helper function: Semantic search in evidence
CREATE OR REPLACE FUNCTION search_evidence_semantic(
    query_embedding vector(1536),
    job_id UUID DEFAULT NULL,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    source_id VARCHAR(64),
    url TEXT,
    title TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.source_id,
        e.url,
        e.title,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM evidence_ledger e
    WHERE
        e.embedding IS NOT NULL
        AND (job_id IS NULL OR e.research_job_id = job_id)
    ORDER BY e.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Helper function: Find similar claims
CREATE OR REPLACE FUNCTION find_similar_claims(
    query_embedding vector(1536),
    job_id UUID DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.8,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    claim_id UUID,
    claim_text TEXT,
    evidence_id UUID,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS claim_id,
        c.claim_text,
        c.evidence_id,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM claims c
    JOIN evidence_ledger e ON c.evidence_id = e.id
    WHERE
        c.embedding IS NOT NULL
        AND (job_id IS NULL OR e.research_job_id = job_id)
        AND 1 - (c.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Helper function: Hybrid search (semantic + keyword)
CREATE OR REPLACE FUNCTION search_evidence_hybrid(
    query_embedding vector(1536),
    query_text TEXT,
    job_id UUID DEFAULT NULL,
    semantic_weight FLOAT DEFAULT 0.7,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    source_id VARCHAR(64),
    url TEXT,
    title TEXT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        SELECT
            e.id,
            e.source_id,
            e.url,
            e.title,
            1 - (e.embedding <=> query_embedding) AS semantic_score
        FROM evidence_ledger e
        WHERE
            e.embedding IS NOT NULL
            AND (job_id IS NULL OR e.research_job_id = job_id)
    ),
    keyword_results AS (
        SELECT
            e.id,
            ts_rank(to_tsvector('english', COALESCE(e.content_text, '')),
                    plainto_tsquery('english', query_text)) AS keyword_score
        FROM evidence_ledger e
        WHERE
            e.content_text IS NOT NULL
            AND (job_id IS NULL OR e.research_job_id = job_id)
    )
    SELECT
        s.id,
        s.source_id,
        s.url,
        s.title,
        (semantic_weight * s.semantic_score +
         (1 - semantic_weight) * COALESCE(k.keyword_score, 0)) AS combined_score
    FROM semantic_results s
    LEFT JOIN keyword_results k ON s.id = k.id
    ORDER BY combined_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON COLUMN evidence_ledger.embedding IS 'Vector embedding for semantic search (1536 dims)';
COMMENT ON COLUMN claims.embedding IS 'Vector embedding for claim similarity matching';
COMMENT ON FUNCTION search_evidence_semantic IS 'Find semantically similar evidence sources';
COMMENT ON FUNCTION find_similar_claims IS 'Find claims similar to a query embedding';
COMMENT ON FUNCTION search_evidence_hybrid IS 'Combined semantic + keyword search';
