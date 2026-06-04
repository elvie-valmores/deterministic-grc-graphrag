from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

# Import our database connection and models from the previous step
from database.staging_client import get_db, StagingMapping, ApprovalStatus

# 1. Initialize the FastAPI Application
app = FastAPI(
    title="Deterministic GRC GraphRAG API",
    description="API for ingesting, validating, and committing compliance mappings.",
    version="1.0.0"
)

# ---------------------------------------------------------
# 2. Pydantic Schemas (Strict Data Validation)
# ---------------------------------------------------------
# These schemas act as a strict bouncer at the door of our API.
# If a request doesn't perfectly match these data types, it gets rejected.
class MappingCreate(BaseModel):
    framework: str
    clause: str
    internal_policy: str
    relationship: str
    notes: Optional[str] = None

class MappingResponse(MappingCreate):
    id: int
    status: ApprovalStatus

    class Config:
        from_attributes = True # Allows Pydantic to read SQLAlchemy ORM objects

# ---------------------------------------------------------
# 3. Human-In-The-Loop (HITL) Endpoints
# ---------------------------------------------------------

@app.post("/api/v1/staging/mappings", response_model=MappingResponse)
def create_pending_mapping(mapping: MappingCreate, db: Session = Depends(get_db)):
    """
    Receives extracted JSON from the LLM pipeline and saves it as PENDING.
    """
    # Convert the validated Pydantic model into a SQLAlchemy database object
    db_mapping = StagingMapping(**mapping.model_dump())
    
    # Save it to Postgres
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping) # Refreshes the object to get the auto-generated ID
    return db_mapping

@app.get("/api/v1/staging/mappings/pending", response_model=List[MappingResponse])
def get_pending_mappings(db: Session = Depends(get_db)):
    """
    Allows a human GRC analyst to view all mappings waiting for approval.
    """
    # Query Postgres for all rows where status == PENDING
    return db.query(StagingMapping).filter(StagingMapping.status == ApprovalStatus.PENDING).all()

@app.post("/api/v1/staging/approve/{mapping_id}")
def approve_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """
    The Human-in-the-Loop approval switch. Changes status to APPROVED.
    """
    # Find the specific mapping by its ID
    mapping = db.query(StagingMapping).filter(StagingMapping.id == mapping_id).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    # Update the status and save to database
    mapping.status = ApprovalStatus.APPROVED
    db.commit()
    
    return {"message": f"Mapping {mapping_id} officially APPROVED.", "status": "APPROVED"}