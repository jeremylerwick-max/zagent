"""add pgvector embeddings

Revision ID: 20260202_0002
Revises: 20260202_0001
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260202_0002"
down_revision = "20260202_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table(
        "source_embedding",
        sa.Column("embedding_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Text(), sa.ForeignKey("source_document.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.text("vector(768)"), nullable=False),  # nomic-embed-text = 768 dim
    )
    op.create_index("uq_source_embedding_chunk", "source_embedding", ["source_id", "chunk_index"], unique=True)
    op.create_index("idx_source_embedding_job", "source_embedding", ["job_id"], unique=False)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_embedding_cosine
        ON source_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_source_embedding_cosine;")
    op.drop_index("idx_source_embedding_job", table_name="source_embedding")
    op.drop_index("uq_source_embedding_chunk", table_name="source_embedding")
    op.drop_table("source_embedding")
