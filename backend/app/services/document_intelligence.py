import json
import logging
import os
from typing import Any, Dict, Optional, Tuple
from pypdf import PdfReader
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Document, DocumentExtraction, DocumentExtractionRevision
from app.providers.factory import get_ai_provider

logger = logging.getLogger(__name__)

class ExtractedFieldDetail(BaseModel):
    value: Optional[Any] = None
    supporting_text_snippet: Optional[str] = None
    page_number: Optional[int] = None
    confidence_heuristic: float = Field(default=0.8, ge=0.0, le=1.0)
    validation_status: str = Field(default="valid") # valid, missing, ambiguous, invalid

class PropertyInquiryExtractionSchema(BaseModel):
    customer_name: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    email: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    phone: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    inquiry_source: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    preferred_location: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    property_type: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    budget: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    bedrooms: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    preference: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    requirements: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)
    inquiry_date: ExtractedFieldDetail = Field(default_factory=ExtractedFieldDetail)

class DocumentIntelligenceService:
    def extract_text_from_file(self, file_path: str, mime_type: str) -> Tuple[str, int]:
        """
        Extracts raw text and total page count using pypdf for PDF documents.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found at {file_path}")

        extracted_text = ""
        page_count = 1

        if mime_type == "application/pdf" or file_path.lower().endswith(".pdf"):
            try:
                reader = PdfReader(file_path)
                page_count = len(reader.pages)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages_text.append(f"--- Page {idx + 1} ---\n{text}")
                extracted_text = "\n\n".join(pages_text)
            except Exception as e:
                logger.warning(f"Error parsing PDF with pypdf: {e}")
                extracted_text = f"Binary PDF document (length: {os.path.getsize(file_path)} bytes)"
        else:
            extracted_text = f"Image Document: {os.path.basename(file_path)}"

        return extracted_text.strip(), page_count

    async def process_document(self, document_id: str, session: AsyncSession) -> DocumentExtraction:
        """
        Executes the extraction pipeline:
        1. Reads document record and validates storage file.
        2. Extracts raw text with pypdf.
        3. Invokes Google Gemini structured output to extract fields with supporting evidence.
        4. Validates confidence and assigns review status.
        5. Persists DocumentExtraction record.
        """
        stmt = select(Document).where(Document.id == document_id)
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        doc.processing_status = "processing"
        await session.commit()

        try:
            raw_text, page_count = self.extract_text_from_file(doc.storage_path, doc.mime_type)
            doc.raw_text = raw_text

            ai_provider = get_ai_provider()

            prompt = (
                f"You are the DocuFlow Document Intelligence specialist analyzing a real estate inquiry document.\n"
                f"Document Name: {doc.original_name}\n"
                f"Document Content:\n{raw_text[:8000]}\n\n"
                f"Extract the requested property inquiry fields. For every field, provide:\n"
                f"- value (null if not mentioned in document)\n"
                f"- supporting_text_snippet (exact text snippet from document justifying extraction, or null)\n"
                f"- page_number (integer page where snippet was found, or null)\n"
                f"- confidence_heuristic (float between 0.0 and 1.0)\n"
                f"- validation_status ('valid', 'missing', 'ambiguous')\n"
                f"CRITICAL RULES: Do NOT fabricate information. If a field is not present, value must be null.\n"
                f"Never claim legal verification or authenticity from extracted text alone."
            )

            structured_result: PropertyInquiryExtractionSchema = await ai_provider.generate_structured_response(
                prompt=prompt,
                response_schema=PropertyInquiryExtractionSchema,
                system_instruction="You are an enterprise document intelligence parser extracting structured property inquiries with evidence."
            )

            # Build metadata dictionary
            metadata_dict = {}
            for field_name in PropertyInquiryExtractionSchema.model_fields.keys():
                field_data: ExtractedFieldDetail = getattr(structured_result, field_name)
                metadata_dict[field_name] = {
                    "snippet": field_data.supporting_text_snippet,
                    "page": field_data.page_number,
                    "confidence": field_data.confidence_heuristic,
                    "status": field_data.validation_status
                }

            # Check if review is required (e.g. missing name/email/phone or low confidence)
            cust_name = structured_result.customer_name.value
            cust_email = structured_result.email.value
            cust_phone = structured_result.phone.value

            needs_review = False
            if not cust_name or (not cust_email and not cust_phone):
                needs_review = True
            for f_name, f_meta in metadata_dict.items():
                if f_meta.get("confidence", 1.0) < 0.65 or f_meta.get("status") == "ambiguous":
                    needs_review = True
                    break

            # Helper for bedroom int conversion
            bedrooms_val = None
            if structured_result.bedrooms.value is not None:
                try:
                    bedrooms_val = int(structured_result.bedrooms.value)
                except (ValueError, TypeError):
                    bedrooms_val = None

            extraction = DocumentExtraction(
                organization_id=doc.organization_id,
                document_id=doc.id,
                customer_name=str(cust_name) if cust_name else None,
                email=str(cust_email) if cust_email else None,
                phone=str(cust_phone) if cust_phone else None,
                inquiry_source=str(structured_result.inquiry_source.value) if structured_result.inquiry_source.value else "Document Upload",
                preferred_location=str(structured_result.preferred_location.value) if structured_result.preferred_location.value else None,
                property_type=str(structured_result.property_type.value) if structured_result.property_type.value else None,
                budget=str(structured_result.budget.value) if structured_result.budget.value else None,
                bedrooms=bedrooms_val,
                preference=str(structured_result.preference.value) if structured_result.preference.value else "Buy",
                requirements=str(structured_result.requirements.value) if structured_result.requirements.value else None,
                inquiry_date=str(structured_result.inquiry_date.value) if structured_result.inquiry_date.value else None,
                field_metadata_json=metadata_dict,
                review_status="review_required" if needs_review else "approved"
            )

            session.add(extraction)
            doc.processing_status = "review_required" if needs_review else "completed"
            await session.commit()
            await session.refresh(extraction)
            return extraction

        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {e}")
            doc.processing_status = "failed"
            doc.error_message = str(e)
            await session.commit()
            raise

    async def update_reviewed_extraction(
        self,
        extraction_id: str,
        updated_fields: Dict[str, Any],
        modified_by_id: str,
        change_reason: str,
        session: AsyncSession
    ) -> DocumentExtraction:
        """
        Updates extraction with human corrections and stores a traceable revision.
        """
        stmt = select(DocumentExtraction).where(DocumentExtraction.id == extraction_id)
        res = await session.execute(stmt)
        extraction = res.scalar_one_or_none()
        if not extraction:
            raise ValueError(f"Extraction with ID {extraction_id} not found.")

        # Snapshot current state
        previous_data = {
            "customer_name": extraction.customer_name,
            "email": extraction.email,
            "phone": extraction.phone,
            "preferred_location": extraction.preferred_location,
            "property_type": extraction.property_type,
            "budget": extraction.budget,
            "bedrooms": extraction.bedrooms,
            "preference": extraction.preference,
            "requirements": extraction.requirements,
        }

        # Apply updates
        for field, value in updated_fields.items():
            if hasattr(extraction, field):
                setattr(extraction, field, value)

        extraction.review_status = "reviewed"

        # Record revision
        rev = DocumentExtractionRevision(
            extraction_id=extraction.id,
            modified_by_id=modified_by_id,
            previous_data_json=previous_data,
            new_data_json=updated_fields,
            change_reason=change_reason
        )
        session.add(rev)
        await session.commit()
        await session.refresh(extraction)
        return extraction

document_intelligence_service = DocumentIntelligenceService()

