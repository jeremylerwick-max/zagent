"""claim-citation linking + citation dedupe

Revision ID: 20260202_0003
Revises: 20260202_0002
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa

revision = "20260202_0003"
down_revision = "20260202_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_source_citation_dedup", "source_citation",
        ["source_id", "quote", "location"], unique=True,
    )
    op.create_table(
        "claim_citation_link",
        sa.Column("claim_id", sa.BigInteger(), sa.ForeignKey("source_claim.claim_id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("citation_id", sa.BigInteger(), sa.ForeignKey("source_citation.citation_id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )
    op.create_index("idx_claim_citation_link_claim", "claim_citation_link", ["claim_id"], unique=False)
    op.create_index("idx_claim_citation_link_citation", "claim_citation_link", ["citation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_claim_citation_link_citation", table_name="claim_citation_link")
    op.drop_index("idx_claim_citation_link_claim", table_name="claim_citation_link")
    op.drop_table("claim_citation_link")
    op.drop_index("uq_source_citation_dedup", table_name="source_citation")
