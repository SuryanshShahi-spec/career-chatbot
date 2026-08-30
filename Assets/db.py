from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

# Create engine (SQLite by default, can be overridden by environment variable)
DB_URL = os.getenv("CELERY_DB_URL", "sqlite:///./worker_app.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__="users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, unique=True, nullable=False)

    # NEW: Store choice ("Immediate", "Daily" , "Weekly", "ON")
    notification_preference = Column(String, default="Daily")

class MatchRecord(Base):
    __tablename__ = "match_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    job_title = Column(String)
    company = Column(String)
    sent_in_daily = Column(Boolean, default=False)
    sent_in_weekly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Ensure tables are created
Base.metadata.create_all(bind=engine)
    