"""SQLAlchemy ORM models for all database tables."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime,
    ForeignKey, Index, JSON, Enum as SAEnum,
)
from sqlalchemy.orm import relationship, DeclarativeBase
from app.domain.enums import (
    PageSource, ScrapeStatus, JobStatus, JobStage,
    IssueSeverity, IssueSource, ExclusionRuleType,
)


class Base(DeclarativeBase):
    pass


# ──────────────────────────── Projects ────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_url = Column(String(2048), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    exclusion_profiles = relationship("ExclusionProfile", back_populates="project", cascade="all, delete-orphan")
    scan_jobs = relationship("ScanJob", back_populates="project", cascade="all, delete-orphan")


# ──────────────────────────── Guidelines ────────────────────────────

class GuidelineSet(Base):
    __tablename__ = "guideline_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    versions = relationship("GuidelineVersion", back_populates="guideline_set", cascade="all, delete-orphan")


class GuidelineVersion(Base):
    __tablename__ = "guideline_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guideline_set_id = Column(Integer, ForeignKey("guideline_sets.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_manifest_json = Column(JSON, nullable=True)
    extracted_text_hash = Column(String(64), nullable=True)
    prompt_version = Column(String(100), nullable=True)
    model_used = Column(String(100), nullable=True)

    guideline_set = relationship("GuidelineSet", back_populates="versions")
    rules = relationship("GuidelineRule", back_populates="guideline_version", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_guideline_versions_set_version", "guideline_set_id", "version_number", unique=True),
    )


class GuidelineRule(Base):
    __tablename__ = "guideline_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guideline_version_id = Column(Integer, ForeignKey("guideline_versions.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    severity_default = Column(SAEnum(IssueSeverity), default=IssueSeverity.MEDIUM)
    rule_text = Column(Text, nullable=False)
    fix_template = Column(Text, nullable=True)
    examples_good = Column(Text, nullable=True)
    examples_bad = Column(Text, nullable=True)
    source_file = Column(String(512), nullable=True)
    section_ref = Column(String(255), nullable=True)

    guideline_version = relationship("GuidelineVersion", back_populates="rules")
    embeddings = relationship("GuidelineRuleEmbedding", back_populates="guideline_rule", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_guideline_rules_rule_id", "rule_id"),
    )


class GuidelineRuleEmbedding(Base):
    __tablename__ = "guideline_rule_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guideline_rule_id = Column(Integer, ForeignKey("guideline_rules.id", ondelete="CASCADE"), nullable=False)
    # Store embedding as JSON array for now; pgvector Column(Vector(1536)) in production
    embedding = Column(JSON, nullable=True)

    guideline_rule = relationship("GuidelineRule", back_populates="embeddings")


# ──────────────────────────── Exclusions ────────────────────────────

class ExclusionProfile(Base):
    __tablename__ = "exclusion_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="exclusion_profiles")
    rules = relationship("ExclusionRule", back_populates="profile", cascade="all, delete-orphan")


class ExclusionRule(Base):
    __tablename__ = "exclusion_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("exclusion_profiles.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(SAEnum(ExclusionRuleType), nullable=False)
    rule_value = Column(String(1024), nullable=False)
    reason = Column(String(512), nullable=True)

    profile = relationship("ExclusionProfile", back_populates="rules")


# ──────────────────────────── Scan Jobs ────────────────────────────

class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    guideline_version_id = Column(Integer, ForeignKey("guideline_versions.id", ondelete="SET NULL"), nullable=True)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    stage = Column(SAEnum(JobStage), nullable=True)
    progress_json = Column(JSON, nullable=True)
    error_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Options stored for reproducibility
    options_json = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="scan_jobs")
    guideline_version = relationship("GuidelineVersion")
    pages = relationship("ScanPage", back_populates="scan_job", cascade="all, delete-orphan")


class ScanPage(Base):
    __tablename__ = "scan_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    selected = Column(Boolean, default=True)
    source = Column(SAEnum(PageSource), nullable=True)
    scrape_status = Column(SAEnum(ScrapeStatus), default=ScrapeStatus.PENDING)

    scan_job = relationship("ScanJob", back_populates="pages")
    chunks = relationship("PageContentChunk", back_populates="scan_page", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="scan_page", cascade="all, delete-orphan")


class PageContentChunk(Base):
    __tablename__ = "page_content_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_page_id = Column(Integer, ForeignKey("scan_pages.id", ondelete="CASCADE"), nullable=False)
    heading_path = Column(String(1024), nullable=True)
    content_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    token_estimate = Column(Integer, nullable=True)

    scan_page = relationship("ScanPage", back_populates="chunks")

    __table_args__ = (
        Index("ix_page_content_chunks_hash", "content_hash"),
    )


# ──────────────────────────── Issues ────────────────────────────

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_page_id = Column(Integer, ForeignKey("scan_pages.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    severity = Column(SAEnum(IssueSeverity), nullable=False)
    evidence = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    proposed_fix = Column(Text, nullable=True)
    guideline_rule_id = Column(Integer, ForeignKey("guideline_rules.id", ondelete="SET NULL"), nullable=True)
    source = Column(SAEnum(IssueSource), nullable=False)
    confidence = Column(Float, default=0.0)
    fingerprint = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan_page = relationship("ScanPage", back_populates="issues")
    guideline_rule = relationship("GuidelineRule")

    __table_args__ = (
        Index("ix_issues_scan_page_id", "scan_page_id"),
        Index("ix_issues_fingerprint", "fingerprint"),
    )


# ──────────────────────────── Prompt Versions ────────────────────────────

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    template = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
