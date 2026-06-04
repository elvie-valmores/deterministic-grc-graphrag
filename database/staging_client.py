from sqlalchemy import create_engine, Column, Integer, String, Enum, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

# 1. Connection String: This matches the credentials in your docker-compose.yml
# Format: postgresql://username:password@localhost:port/database_name
DATABASE_URL = "postgresql://admin:adminpassword@localhost:5432/grc_staging"

# 2. Initialize SQLAlchemy Engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 3. Define the Staging Status Enum
class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

# 4. Define the Database Table Schema
class StagingMapping(Base):
    __tablename__ = "compliance_mappings"

    id = Column(Integer, primary_key=True, index=True)
    framework = Column(String, index=True)
    clause = Column(String, index=True)
    internal_policy = Column(String)
    relationship = Column(String)
    
    # Every new mapping defaults to PENDING
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    
    # Optional: A place to store raw notes or LLM confidence reasoning
    notes = Column(Text, nullable=True)

# 5. Create the tables in the database
def init_db():
    print("Initializing Staging Database...")
    Base.metadata.create_all(bind=engine)
    print("Staging Database Initialized Successfully.")

# Dependency to get the database session in our FastAPI routes later
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()