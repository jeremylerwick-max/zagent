-- V001: Initialize Evidence Ledger tables
-- Deep Research Engine - Core Schema
--
-- Key Principle: Append-only, immutable evidence records.
-- Once evidence is written, it can never be modified.

-- Research jobs (the parent record)
CREATE TABLE IF NOT EXISTS research_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Request
    user_query TEXT NOT NULL,
    research_objective TEXT,

    -- Planning
    sub_questions JSONB DEFAULT '[]',
    stopping_criteria JSONB,

    -- Budget
    max_queries INTEGER DEFAULT 20,
    max_tokens INTEGER DEFAULT 500000,
    max_time_seconds INTEGER DEFAULT 600,
    confidence_threshold DECIMAL(3,2) DEFAULT 0.80,

    -- State
    status VARCHAR(20) DEFAULT 'planning'
        CHECK (status IN ('planning', 'searching', 'extracting', 'verifying', 'synthesizing', 'completed', 'failed')),
    current_node VARCHAR(30),
    iteration_count INTEGER DEFAULT 0,

    -- Budget consumption
    queries_used INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,

    -- Results
    final_report TEXT,
    final_confidence DECIMAL(3,2),

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Evidence ledger (IMMUTABLE - the "secret sauce")
CREATE TABLE IF NOT EXISTS evidence_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id VARCHAR(64) NOT NULL UNIQUE,  -- SHA256(url + timestamp)

    -- Source metadata
    url TEXT NOT NULL,
    title TEXT,
    domain VARCHAR(255),
    retrieved_at TIMESTAMPTZ DEFAULT NOW(),
    content_hash VARCHAR(64) NOT NULL,  -- SHA256 of raw content

    -- Reliability
    reliability_score DECIMAL(3,2) CHECK (reliability_score BETWEEN 0 AND 1),
    source_type VARCHAR(20) CHECK (source_type IN ('web', 'pdf', 'api', 'corpus')),

    -- Research job linkage
    research_job_id UUID REFERENCES research_jobs(id) ON DELETE CASCADE,
    used_in_final BOOLEAN DEFAULT FALSE,

    -- Audit (immutable)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRITICAL: Make evidence_ledger append-only
-- This trigger prevents any UPDATE or DELETE operations
CREATE OR REPLACE FUNCTION prevent_evidence_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Only allow updating used_in_final flag
        IF OLD.source_id = NEW.source_id
           AND OLD.url = NEW.url
           AND OLD.content_hash = NEW.content_hash
           AND OLD.created_at = NEW.created_at
        THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'Evidence ledger records are immutable. Only used_in_final can be updated.';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Evidence ledger records cannot be deleted.';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER evidence_immutable
    BEFORE UPDATE OR DELETE ON evidence_ledger
    FOR EACH ROW
    EXECUTE FUNCTION prevent_evidence_modification();

-- Claims extracted from evidence
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID REFERENCES evidence_ledger(id) ON DELETE CASCADE,

    -- Claim content
    claim_text TEXT NOT NULL,
    claim_type VARCHAR(20) CHECK (claim_type IN ('fact', 'estimate', 'opinion', 'prediction')),
    confidence DECIMAL(3,2) CHECK (confidence BETWEEN 0 AND 1),

    -- Location in source
    location_hint TEXT,

    -- Entities extracted
    entities JSONB DEFAULT '[]',

    -- Verification status
    verified BOOLEAN DEFAULT FALSE,
    contradicted_by UUID REFERENCES claims(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Direct quotes (max 25 words for copyright compliance)
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID REFERENCES evidence_ledger(id) ON DELETE CASCADE,
    claim_id UUID REFERENCES claims(id),

    quote_text VARCHAR(200) NOT NULL,  -- ~25 words max
    quote_location TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Verification reports
CREATE TABLE IF NOT EXISTS verification_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_job_id UUID REFERENCES research_jobs(id) ON DELETE CASCADE,

    -- Findings
    contradictions JSONB DEFAULT '[]',
    gaps JSONB DEFAULT '[]',
    weak_claims JSONB DEFAULT '[]',  -- Single-source claims
    falsification_criteria TEXT,

    -- Assessment
    overall_confidence DECIMAL(3,2),
    recommend_more_research BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_evidence_job ON evidence_ledger(research_job_id);
CREATE INDEX IF NOT EXISTS idx_evidence_domain ON evidence_ledger(domain);
CREATE INDEX IF NOT EXISTS idx_evidence_source_id ON evidence_ledger(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_evidence ON claims(evidence_id);
CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_citations_evidence ON citations(evidence_id);
CREATE INDEX IF NOT EXISTS idx_citations_claim ON citations(claim_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON research_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON research_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verification_job ON verification_reports(research_job_id);

-- Comments for documentation
COMMENT ON TABLE evidence_ledger IS 'Immutable, append-only record of all evidence sources';
COMMENT ON TABLE claims IS 'Claims extracted from evidence with confidence scores';
COMMENT ON TABLE citations IS 'Direct quotes from sources (max 25 words)';
COMMENT ON TABLE research_jobs IS 'Parent record for research sessions';
COMMENT ON TABLE verification_reports IS 'Contradiction and gap analysis results';
