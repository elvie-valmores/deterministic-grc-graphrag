from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.staging_client import get_db, StagingMapping, ApprovalStatus, LifecycleStatus
from database.neo4j_client import graph_db

app = FastAPI(title="Deterministic GRC GraphRAG API", version="1.1.0")

class MappingCreate(BaseModel):
    framework: str
    clause: str
    internal_policy: str
    relationship: str
    notes: Optional[str] = None
    version: str = "1.0"  # Added versioning

class MappingResponse(MappingCreate):
    id: int
    status: ApprovalStatus
    lifecycle_status: LifecycleStatus
    is_deleted: bool

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
    # Filter out anything that has been "soft deleted"
    return db.query(StagingMapping).filter(
        StagingMapping.status == ApprovalStatus.PENDING,
        StagingMapping.is_deleted == False
    ).all()

# --- NEW: Phase 1 Soft Delete Endpoint ---
@app.delete("/api/v1/staging/mappings/{mapping_id}")
def soft_delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(StagingMapping).filter(StagingMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    mapping.is_deleted = True  # Flip the switch instead of actually deleting
    db.commit()
    return {"message": f"Mapping {mapping_id} safely soft-deleted."}

@app.post("/api/v1/staging/approve/{mapping_id}")
def approve_mapping(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(StagingMapping).filter(
        StagingMapping.id == mapping_id, 
        StagingMapping.is_deleted == False
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found or deleted")
    
    # --- NEW: Phase 1 Retirement Logic ---
    # Find active, older versions of this exact policy and retire them
    old_versions = db.query(StagingMapping).filter(
        StagingMapping.internal_policy == mapping.internal_policy,
        StagingMapping.framework == mapping.framework,
        StagingMapping.clause == mapping.clause,
        StagingMapping.lifecycle_status == LifecycleStatus.ACTIVE,
        StagingMapping.id != mapping_id
    ).all()

    for old in old_versions:
        old.lifecycle_status = LifecycleStatus.RETIRED

    mapping.status = ApprovalStatus.APPROVED
    db.commit()
    return {"message": f"Mapping {mapping_id} APPROVED. Previous versions retired."}

@app.post("/api/v1/staging/commit/{mapping_id}")
def commit_to_graph(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(StagingMapping).filter(StagingMapping.id == mapping_id).first()
    if not mapping or mapping.status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Invalid mapping or not approved.")
    
    try:
        graph_db.commit_mapping_to_graph(
            framework=mapping.framework,
            clause=mapping.clause,
            internal_policy=mapping.internal_policy,
            relationship=mapping.relationship,
            version=mapping.version # Pass the version to the graph
        )
        return {"message": f"Mapping {mapping_id} committed to Neo4j!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Error: {e}")

@app.get("/api/v1/compliance/search")
def search_compliance_graph(clause: str):
    try:
        results = graph_db.get_policies_by_clause(clause_name=clause)
        return {"clause_searched": clause, "total_policies_found": len(results), "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search Query Failed: {e}")