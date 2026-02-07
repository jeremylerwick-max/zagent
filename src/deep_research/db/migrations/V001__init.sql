-- V001__init.sql
BEGIN;

CREATE TABLE IF NOT EXISTS research_job (
  job_id            UUID PRIMARY KEY,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id           TEXT NULL,
  query             TEXT NOT NULL,
  objective         TEXT NULL,
  subquestions      JSONB NOT NULL DEFAULT '[]'::jsonb,
  stopping_criteria JSONB NOT NULL DEFAULT '{}'::jsonb,
  budgets           JSONB NOT NULL DEFAULT '{}'::jsonb,
  status            TEXT NOT NULL DEFAULT 'running',
  error             TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_research_job_created_at ON research_job (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_job_status ON research_job (status);

CREATE TABLE IF NOT EXISTS source_document (
  source_id      TEXT PRIMARY KEY,
  job_id         UUID NOT NULL REFERENCES research_job(job_id) ON DELETE CASCADE,
  url            TEXT NOT NULL,
  retrieved_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  mime_type      TEXT NOT NULL,
  content_hash   TEXT NOT NULL,
  text           TEXT NOT NULL,
  metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
  provider       TEXT NULL,
  reliability_score NUMERIC(4,3) NOT NULL DEFAULT 0.500,
  used_in_final  BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_source_document_job_id ON source_document (job_id);
CREATE INDEX IF NOT EXISTS idx_source_document_url ON source_document (url);

-- Append-only enforcement
CREATE OR REPLACE FUNCTION deny_mutation_except_admin()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'source_document is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_source_document_no_update ON source_document;
CREATE TRIGGER trg_source_document_no_update
BEFORE UPDATE ON source_document
FOR EACH ROW EXECUTE FUNCTION deny_mutation_except_admin();

DROP TRIGGER IF EXISTS trg_source_document_no_delete ON source_document;
CREATE TRIGGER trg_source_document_no_delete
BEFORE DELETE ON source_document
FOR EACH ROW EXECUTE FUNCTION deny_mutation_except_admin();

CREATE TABLE IF NOT EXISTS source_claim (
  claim_id     BIGSERIAL PRIMARY KEY,
  job_id       UUID NOT NULL REFERENCES research_job(job_id) ON DELETE CASCADE,
  source_id    TEXT NOT NULL REFERENCES source_document(source_id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  claim_text   TEXT NOT NULL,
  claim_type   TEXT NOT NULL CHECK (claim_type IN ('fact','estimate','opinion')),
  confidence   NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  entities     JSONB NOT NULL DEFAULT '[]'::jsonb,
  numbers      JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_source_claim_job ON source_claim (job_id);
CREATE INDEX IF NOT EXISTS idx_source_claim_source ON source_claim (source_id);

CREATE TABLE IF NOT EXISTS source_citation (
  citation_id  BIGSERIAL PRIMARY KEY,
  job_id       UUID NOT NULL REFERENCES research_job(job_id) ON DELETE CASCADE,
  source_id    TEXT NOT NULL REFERENCES source_document(source_id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  quote        TEXT NOT NULL,
  location     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_source_citation_job ON source_citation (job_id);

CREATE TABLE IF NOT EXISTS verification_finding (
  finding_id   BIGSERIAL PRIMARY KEY,
  job_id       UUID NOT NULL REFERENCES research_job(job_id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  severity     TEXT NOT NULL CHECK (severity IN ('low','med','high')),
  finding      TEXT NOT NULL,
  related_source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  recommended_action TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verification_job ON verification_finding (job_id);

CREATE TABLE IF NOT EXISTS final_report (
  job_id       UUID PRIMARY KEY REFERENCES research_job(job_id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  outline      TEXT NULL,
  answer       TEXT NOT NULL,
  confidence   NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  used_source_ids JSONB NOT NULL DEFAULT '[]'::jsonb
);

COMMIT;
