"""init deep research schema

Revision ID: 20260202_0001
Revises:
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260202_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_job",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("subquestions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("stopping_criteria", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("budgets", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'running'"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("idx_research_job_created_at", "research_job", ["created_at"], unique=False)
    op.create_index("idx_research_job_status", "research_job", ["status"], unique=False)

    op.create_table(
        "source_document",
        sa.Column("source_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("reliability_score", sa.Numeric(4, 3), server_default=sa.text("0.500"), nullable=False),
        sa.Column("used_in_final", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index("idx_source_document_job_id", "source_document", ["job_id"], unique=False)
    op.create_index("idx_source_document_url", "source_document", ["url"], unique=False)
    op.create_index("idx_source_document_used", "source_document", ["job_id", "used_in_final"], unique=False)

    op.execute("""
        CREATE OR REPLACE FUNCTION source_document_guard()
        RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'source_document is append-only (delete denied)';
          END IF;
          IF TG_OP = 'UPDATE' THEN
            IF (OLD.used_in_final = false AND NEW.used_in_final = true)
               AND NEW.reliability_score = OLD.reliability_score AND NEW.job_id = OLD.job_id
               AND NEW.url = OLD.url AND NEW.retrieved_at = OLD.retrieved_at
               AND NEW.mime_type = OLD.mime_type AND NEW.content_hash = OLD.content_hash
               AND NEW.text = OLD.text AND NEW.metadata = OLD.metadata
               AND NEW.provider IS NOT DISTINCT FROM OLD.provider
            THEN RETURN NEW; END IF;
            IF (NEW.reliability_score <> OLD.reliability_score)
               AND NEW.used_in_final = OLD.used_in_final AND NEW.job_id = OLD.job_id
               AND NEW.url = OLD.url AND NEW.retrieved_at = OLD.retrieved_at
               AND NEW.mime_type = OLD.mime_type AND NEW.content_hash = OLD.content_hash
               AND NEW.text = OLD.text AND NEW.metadata = OLD.metadata
               AND NEW.provider IS NOT DISTINCT FROM OLD.provider
            THEN RETURN NEW; END IF;
            RAISE EXCEPTION 'source_document immutable (only used_in_final false->true OR reliability_score allowed)';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_source_document_guard_upd ON source_document;")
    op.execute("CREATE TRIGGER trg_source_document_guard_upd BEFORE UPDATE ON source_document FOR EACH ROW EXECUTE FUNCTION source_document_guard();")
    op.execute("DROP TRIGGER IF EXISTS trg_source_document_guard_del ON source_document;")
    op.execute("CREATE TRIGGER trg_source_document_guard_del BEFORE DELETE ON source_document FOR EACH ROW EXECUTE FUNCTION source_document_guard();")

    op.create_table(
        "source_claim",
        sa.Column("claim_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Text(), sa.ForeignKey("source_document.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("entities", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("numbers", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.CheckConstraint("claim_type IN ('fact','estimate','opinion')", name="ck_source_claim_type"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_source_claim_confidence"),
    )
    op.create_index("idx_source_claim_job", "source_claim", ["job_id"], unique=False)
    op.create_index("idx_source_claim_source", "source_claim", ["source_id"], unique=False)

    op.create_table(
        "source_citation",
        sa.Column("citation_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Text(), sa.ForeignKey("source_document.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
    )
    op.create_index("idx_source_citation_job", "source_citation", ["job_id"], unique=False)
    op.create_index("idx_source_citation_source", "source_citation", ["source_id"], unique=False)

    op.create_table(
        "verification_finding",
        sa.Column("finding_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("finding", sa.Text(), nullable=False),
        sa.Column("related_source_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.CheckConstraint("severity IN ('low','med','high')", name="ck_verification_severity"),
    )
    op.create_index("idx_verification_job", "verification_finding", ["job_id"], unique=False)
    op.create_index("idx_verification_severity", "verification_finding", ["job_id", "severity"], unique=False)

    op.create_table(
        "final_report",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_job.job_id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("outline", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("used_source_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_final_report_confidence"),
    )


def downgrade() -> None:
    op.drop_table("final_report")
    op.drop_index("idx_verification_severity", table_name="verification_finding")
    op.drop_index("idx_verification_job", table_name="verification_finding")
    op.drop_table("verification_finding")
    op.drop_index("idx_source_citation_source", table_name="source_citation")
    op.drop_index("idx_source_citation_job", table_name="source_citation")
    op.drop_table("source_citation")
    op.drop_index("idx_source_claim_source", table_name="source_claim")
    op.drop_index("idx_source_claim_job", table_name="source_claim")
    op.drop_table("source_claim")
    op.execute("DROP TRIGGER IF EXISTS trg_source_document_guard_del ON source_document;")
    op.execute("DROP TRIGGER IF EXISTS trg_source_document_guard_upd ON source_document;")
    op.execute("DROP FUNCTION IF EXISTS source_document_guard();")
    op.drop_index("idx_source_document_used", table_name="source_document")
    op.drop_index("idx_source_document_url", table_name="source_document")
    op.drop_index("idx_source_document_job_id", table_name="source_document")
    op.drop_table("source_document")
    op.drop_index("idx_research_job_status", table_name="research_job")
    op.drop_index("idx_research_job_created_at", table_name="research_job")
    op.drop_table("research_job")
