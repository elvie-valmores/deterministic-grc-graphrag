from sqlalchemy import create_engine, Column, Integer, String, Enum, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

# Connection String targeting our Dockerized Postgres
DATABASE_URL = "postgresql://admin:adminpassword@localhost:5432/grc_staging"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

# --- NEW: Phase 1 Lifecycle Tracking ---
class LifecycleStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"

class StagingMapping(Base):
    __tablename__ = "compliance_mappings"

    id = Column(Integer, primary_key=True, index=True)
    framework = Column(String, index=True)
    clause = Column(String, index=True)
    internal_policy = Column(String)
    relationship = Column(String)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    notes = Column(Text, nullable=True)
    
    # --- NEW: Phase 1 Audit Columns ---
    version = Column(String, default="1.0")
    lifecycle_status = Column(Enum(LifecycleStatus), default=LifecycleStatus.ACTIVE)
    is_deleted = Column(Boolean, default=False)  # The Soft Delete flag

def init_db():
    print("Initializing Staging Database...")
    Base.metadata.create_all(bind=engine)
    print("Staging Database Initialized Successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()