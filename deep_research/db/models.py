from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
    Index, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class ResearchJob(Base):
    __tablename__ = "research_job"
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subquestions: Mapped[List[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    stopping_criteria: Mapped[Dict[str, Any]] = mapped_column(JSONB, server_default="{}", nullable=False)
    budgets: Mapped[Dict[str, Any]] = mapped_column(JSONB, server_default="{}", nullable=False)
    status: Mapped[str] = mapped_column(Text, server_default="running", nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sources: Mapped[List["SourceDocument"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    claims: Mapped[List["SourceClaim"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    citations: Mapped[List["SourceCitation"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    findings: Mapped[List["VerificationFinding"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    final_report: Mapped[Optional["FinalReport"]] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")
    embeddings: Mapped[List["SourceEmbedding"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_research_job_created_at", "created_at"),
        Index("idx_research_job_status", "status"),
    )


class SourceDocument(Base):
    __tablename__ = "source_document"
    source_id: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, server_default="{}", nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reliability_score: Mapped[float] = mapped_column(Numeric(4, 3), server_default="0.500", nullable=False)
    used_in_final: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    job: Mapped["ResearchJob"] = relationship(back_populates="sources")
    claims: Mapped[List["SourceClaim"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    citations: Mapped[List["SourceCitation"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    embeddings: Mapped[List["SourceEmbedding"]] = relationship(back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_source_document_job_id", "job_id"),
        Index("idx_source_document_url", "url"),
        Index("idx_source_document_used", "job_id", "used_in_final"),
    )


class SourceClaim(Base):
    __tablename__ = "source_claim"
    claim_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, ForeignKey("source_document.source_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    entities: Mapped[List[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    numbers: Mapped[List[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)

    job: Mapped["ResearchJob"] = relationship(back_populates="claims")
    source: Mapped["SourceDocument"] = relationship(back_populates="claims")

    __table_args__ = (
        CheckConstraint("claim_type IN ('fact','estimate','opinion')", name="ck_source_claim_type"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_source_claim_confidence"),
        Index("idx_source_claim_job", "job_id"),
        Index("idx_source_claim_source", "source_id"),
    )


class SourceCitation(Base):
    __tablename__ = "source_citation"
    citation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, ForeignKey("source_document.source_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["ResearchJob"] = relationship(back_populates="citations")
    source: Mapped["SourceDocument"] = relationship(back_populates="citations")

    __table_args__ = (
        Index("idx_source_citation_job", "job_id"),
        Index("idx_source_citation_source", "source_id"),
        Index("uq_source_citation_dedup", "source_id", "quote", "location", unique=True),
    )


class VerificationFinding(Base):
    __tablename__ = "verification_finding"
    finding_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    related_source_ids: Mapped[List[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["ResearchJob"] = relationship(back_populates="findings")

    __table_args__ = (
        CheckConstraint("severity IN ('low','med','high')", name="ck_verification_severity"),
        Index("idx_verification_job", "job_id"),
        Index("idx_verification_severity", "job_id", "severity"),
    )


class FinalReport(Base):
    __tablename__ = "final_report"
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_job.job_id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    outline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    used_source_ids: Mapped[List[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)

    job: Mapped["ResearchJob"] = relationship(back_populates="final_report")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_final_report_confidence"),
    )


class SourceEmbedding(Base):
    __tablename__ = "source_embedding"
    embedding_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_job.job_id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, ForeignKey("source_document.source_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(768), nullable=False)  # nomic-embed-text = 768 dim

    job: Mapped["ResearchJob"] = relationship(back_populates="embeddings")
    source: Mapped["SourceDocument"] = relationship(back_populates="embeddings")

    __table_args__ = (
        Index("uq_source_embedding_chunk", "source_id", "chunk_index", unique=True),
        Index("idx_source_embedding_job", "job_id"),
    )


class ClaimCitationLink(Base):
    __tablename__ = "claim_citation_link"
    claim_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("source_claim.claim_id", ondelete="CASCADE"), primary_key=True)
    citation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("source_citation.citation_id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index("idx_claim_citation_link_claim", "claim_id"),
        Index("idx_claim_citation_link_citation", "citation_id"),
    )
