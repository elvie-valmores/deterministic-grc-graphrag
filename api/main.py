from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.staging_client import get_db, StagingMapping, ApprovalStatus
from database.neo4j_client import graph_db

app = FastAPI(
    title="Deterministic GRC GraphRAG API",
    description="API for ingesting, validating, and committing compliance mappings.",
    version="1.0.0"
)

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
        from_attributes = True

@app.post("/api/v1/staging/mappings", response_model=MappingResponse)
def create_pending_mapping(mapping: MappingCreate, db: Session = Depends(get_db)):
    db_mapping = StagingMapping(**mapping.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping

@app.get("/api/v1/staging/mappings/pending", response_model=List[MappingResponse])
def get_pending_mappings(db: Session = Depends(get_db)):
    return db.query(StagingMapping).filter(StagingMapping.status == ApprovalStatus.PENDING).all()

@app.post("/api/v1/staging/approve/{mapping_id}")
def approve_mapping(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(StagingMapping).filter(StagingMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    mapping.status = ApprovalStatus.APPROVED
    db.commit()
    return {"message": f"Mapping {mapping_id} officially APPROVED.", "status": "APPROVED"}

@app.post("/api/v1/staging/commit/{mapping_id}")
def commit_to_graph(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(StagingMapping).filter(StagingMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if mapping.status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Cannot commit to graph. Status must be APPROVED.")
    
    try:
        graph_db.commit_mapping_to_graph(
            framework=mapping.framework,
            clause=mapping.clause,
            internal_policy=mapping.internal_policy,
            relationship=mapping.relationship
        )
        return {"message": f"Mapping {mapping_id} successfully committed to Neo4j Knowledge Graph!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Database Error: {e}")