import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = "sqlite:///./dni_voice_agent.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CallLog(Base):
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True, index=True)
    customer_name = Column(String)
    phone_number = Column(String)
    policy_type = Column(String)
    date_of_birth = Column(String, nullable=True)
    emirates_id = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    trade_licence = Column(String, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer, default=0)
    rating = Column(Float, nullable=True)
    status = Column(String, default="completed")
    transcript = Column(String, nullable=True)
    recording_url = Column(String, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
