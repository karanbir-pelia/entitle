"""
Document upload and reading endpoint.
Accepts an image (photo of a government document) and returns a plain-language explanation.
"""

import base64
import logging
import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from models.schemas import DocumentResponse, Language
from services.document_reader import read_document, read_pdf_document
from utils.formatting import safe_parse_json

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | {"application/pdf"}


def _load_document_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "../data/prompts/document_prompt.txt")
    with open(path) as f:
        return f.read()


def _fallback_document_response(summary: str | None = None) -> DocumentResponse:
    return DocumentResponse(
        document_type="Unable to read document",
        plain_language_summary=summary or (
            "Entitle could not read this document right now. The file was received, "
            "but the vision model did not return a usable explanation."
        ),
        action_required="Try again with a clearer photo or a smaller PDF, or review the document with a local benefits helper.",
        next_steps=[
            "Retake the photo in good light with all corners visible",
            "Check the document for any deadline or action date",
            "Call 211 or contact the agency listed on the notice for help",
        ],
    )


@router.post("/document", response_model=DocumentResponse)
async def read_document_endpoint(
    file: UploadFile = File(...),
    language: Language = Form(Language.en),
) -> DocumentResponse:
    """
    Accept an image or PDF of a government document and return a plain-language explanation.
    PDFs are rendered to images (preserving tables and forms) before being sent to the vision model.
    """
    file_data = await file.read()
    mime_type = file.content_type or "image/jpeg"
    language_code = language.value

    if not file_data:
        raise HTTPException(status_code=400, detail="Upload a document file before asking Entitle to read it.")

    if len(file_data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. Upload a document under 8 MB.")

    if mime_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a JPG, PNG, WebP, HEIC, HEIF photo, or a PDF.",
        )

    logger.info(
        "Document upload: filename=%s, mime=%s, size=%d bytes, language=%s",
        file.filename,
        mime_type,
        len(file_data),
        language_code,
    )

    prompt_template = _load_document_prompt()

    try:
        if mime_type == "application/pdf":
            response_text = await read_pdf_document(
                pdf_bytes=file_data,
                language=language_code,
                prompt_template=prompt_template,
            )
        else:
            image_base64 = base64.b64encode(file_data).decode("utf-8")
            response_text = await read_document(
                image_base64=image_base64,
                image_mime_type=mime_type,
                language=language_code,
                prompt_template=prompt_template,
            )
    except Exception as e:
        logger.warning("Document reader unavailable: %s", e)
        return _fallback_document_response()

    # Parse Gemma 4's JSON response
    data = safe_parse_json(response_text, fallback=None)

    if data and isinstance(data, dict):
        try:
            # Gemma sometimes returns a string explanation instead of null/bool for
            # appeal_possible on non-denial documents — coerce to None so Pydantic accepts it.
            if isinstance(data.get("appeal_possible"), str):
                data["appeal_possible"] = None
            return DocumentResponse(**data)
        except Exception as e:
            logger.error("Document response parse error: %s", e)

    summary = response_text[:500] if response_text else None
    return _fallback_document_response(summary)
