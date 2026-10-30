from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import Document, DocumentExtraction
from app.services.storage import storage_service
from app.services.document_intelligence import document_intelligence_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])

class ExtractionReviewSchema(BaseModel):
    updated_fields: Dict[str, Any]
    change_reason: Optional[str] = "Human reviewer modification"

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    upload_res = await storage_service.save_upload(file=file, org_id=member.organization_id)

    doc = Document(
        organization_id=member.organization_id,
        uploaded_by_id=member.user_id,
        filename=upload_res["opaque_filename"],
        original_name=upload_res["original_name"],
        mime_type=upload_res["mime_type"],
        file_size=upload_res["file_size"],
        storage_path=upload_res["storage_path"],
        processing_status="uploaded"
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "id": doc.id,
        "original_name": doc.original_name,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "processing_status": doc.processing_status,
        "created_at": doc.created_at.isoformat()
    }

@router.get("")
async def list_documents(
    status: Optional[str] = None,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Document).where(Document.organization_id == member.organization_id)
    if status:
        stmt = stmt.where(Document.processing_status == status)
    res = await db.execute(stmt.order_by(Document.created_at.desc()).limit(50))
    return res.scalars().all()

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Document).where(and_(Document.id == document_id, Document.organization_id == member.organization_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Check if extraction exists
    e_stmt = select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
    e_res = await db.execute(e_stmt)
    extraction = e_res.scalar_one_or_none()

    return {
        "document": doc,
        "extraction": extraction
    }

@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Document).where(and_(Document.id == document_id, Document.organization_id == member.organization_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    extraction = await document_intelligence_service.process_document(document_id, db)
    return extraction

@router.get("/{document_id}/extraction")
async def get_document_extraction(
    document_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(DocumentExtraction).where(
        and_(DocumentExtraction.document_id == document_id, DocumentExtraction.organization_id == member.organization_id)
    ).order_by(DocumentExtraction.created_at.desc())
    res = await db.execute(stmt)
    extraction = res.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found for this document.")
    return extraction

@router.put("/extractions/{extraction_id}/review")
async def review_extraction(
    extraction_id: str,
    req: ExtractionReviewSchema,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    extraction = await document_intelligence_service.update_reviewed_extraction(
        extraction_id=extraction_id,
        updated_fields=req.updated_fields,
        modified_by_id=member.user_id,
        change_reason=req.change_reason or "Review modification",
        session=db
    )
    return extraction

