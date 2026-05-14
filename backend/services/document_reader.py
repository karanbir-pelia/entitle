"""
Document reader service — wraps the vision pipeline for government document photos
and PDFs (rendered to images so tables and forms are preserved).
"""

import base64
import io
import logging

from services.gemma import generate_with_image

logger = logging.getLogger(__name__)

LANG_MAP = {
    "en": "English",
    "es": "Spanish",
    "zh": "Chinese",
    "vi": "Vietnamese",
    "ar": "Arabic",
    "fr": "French",
    "pt": "Portuguese",
    "ko": "Korean",
    "ru": "Russian",
}

_SYSTEM_PROMPT = (
    "You are a benefits document specialist. "
    "Explain government documents in plain, kind language. "
    "Respond only with valid JSON matching the DocumentResponse schema."
)

_PDF_MAX_PAGES = 3
_PDF_RENDER_SCALE = 1.5   # Higher = more readable but larger image
_LABEL_HEIGHT = 28        # Pixel height for the "--- Page N ---" separator strip


def _pdf_to_combined_image(pdf_bytes: bytes) -> tuple[str, str]:
    """
    Render up to _PDF_MAX_PAGES pages of a PDF to a single PNG.
    Pages are stacked top-to-bottom (Page 1 first) with a labelled divider
    between pages so the vision model understands page order.
    Returns (base64-encoded PNG, mime_type).
    """
    import fitz  # PyMuPDF
    from PIL import Image, ImageDraw, ImageFont

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_pages = min(len(doc), _PDF_MAX_PAGES)
    mat = fitz.Matrix(_PDF_RENDER_SCALE, _PDF_RENDER_SCALE)

    pil_pages: list[Image.Image] = []
    for i in range(n_pages):
        pixmap = doc[i].get_pixmap(matrix=mat)
        pil_pages.append(Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB"))
    doc.close()

    if len(pil_pages) == 1:
        combined = pil_pages[0]
    else:
        max_width = max(img.width for img in pil_pages)
        total_height = sum(img.height for img in pil_pages) + _LABEL_HEIGHT * (n_pages - 1)
        combined = Image.new("RGB", (max_width, total_height), "white")
        draw = ImageDraw.Draw(combined)
        y = 0
        for idx, img in enumerate(pil_pages):
            combined.paste(img, (0, y))
            y += img.height
            if idx < n_pages - 1:
                # Draw a separator labelled "--- Page N+1 ---" so page order is explicit
                draw.rectangle([0, y, max_width, y + _LABEL_HEIGHT], fill="#e0e0e0")
                label = f"─── Page {idx + 2} of {n_pages} ───"
                draw.text((10, y + 6), label, fill="#333333")
                y += _LABEL_HEIGHT

    buf = io.BytesIO()
    combined.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    logger.info(
        "PDF rendered: pages=%d, combined=%dx%d, encoded_bytes=%d",
        n_pages, combined.width, combined.height, len(encoded),
    )
    return encoded, "image/png"


async def read_pdf_document(
    pdf_bytes: bytes,
    language: str = "en",
    prompt_template: str = "",
) -> str:
    """
    Render a PDF to an image and send it to Gemma 4 vision.
    Pages are composited Page 1 on top → Page N on bottom with visible labels.
    Returns raw text response — caller parses JSON.
    """
    lang_name = LANG_MAP.get(language, "English")
    prompt = prompt_template.replace("{language}", lang_name)

    logger.info("Reading PDF: language=%s, size=%d bytes", language, len(pdf_bytes))

    image_base64, mime_type = _pdf_to_combined_image(pdf_bytes)
    return await generate_with_image(
        text_prompt=prompt,
        image_base64=image_base64,
        image_mime_type=mime_type,
        system_prompt=_SYSTEM_PROMPT,
    )


async def read_document(
    image_base64: str,
    image_mime_type: str = "image/jpeg",
    language: str = "en",
    prompt_template: str = "",
) -> str:
    """
    Send an image to Gemma 4 vision and return the raw text response.
    Caller is responsible for parsing the JSON.
    """
    lang_name = LANG_MAP.get(language, "English")
    prompt = prompt_template.replace("{language}", lang_name)

    logger.info("Reading document: mime_type=%s, language=%s", image_mime_type, language)

    return await generate_with_image(
        text_prompt=prompt,
        image_base64=image_base64,
        image_mime_type=image_mime_type,
        system_prompt=_SYSTEM_PROMPT,
    )
