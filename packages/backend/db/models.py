"""Database models and initialization. Phase 1: no-op (in-memory only)."""

import logging

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database connection. Phase 1: schema-only, no actual DB."""
    logger.info('Database init skipped (Phase 1 - using in-memory storage)')


# SQLAlchemy models for Phase 2+:
# from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
# from sqlalchemy.ext.declarative import declarative_base
#
# Base = declarative_base()
#
# class Job(Base):
#     __tablename__ = 'jobs'
#     id = Column(String, primary_key=True)
#     topic = Column(String, nullable=False)
#     status = Column(String, default='queued')
#     created_at = Column(DateTime)
#     updated_at = Column(DateTime)
#
# class Result(Base):
#     __tablename__ = 'results'
#     id = Column(Integer, primary_key=True)
#     job_id = Column(String, ForeignKey('jobs.id'))
#     final_output = Column(Text)
#     context = Column(JSON)
