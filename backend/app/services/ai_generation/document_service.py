"""
services/ai_generation/document_service.py
============================================
Document summarisation feature — PLACEHOLDER.

CURRENT STATE:  Not implemented.

PLANNED USE CASES:
    - Summarise a research paper → key points for slides
    - Extract eligibility criteria from government scheme PDF
    - Summarise codebase README for the architecture slide

HOW TO IMPLEMENT:
    - Use existing Groq client (already in ppt_service)
    - Feed PDF text through pdfplumber (already imported in ppt_service)
    - Prompt: "Summarise this document in 5 bullet points for a hackathon presentation"

WIRING CHECKLIST:
    [ ] Add "document_summary": 3 to config.CREDIT_COSTS (already there)
    [ ] Implement run() below
    [ ] Add POST /generate/summarise route in routes/generate.py
"""

import logging
from app.services.ai_generation.base import AIFeature

log = logging.getLogger(__name__)


class DocumentSummaryService(AIFeature):
    """
    Document summarisation feature.
    Credits and rate limiting handled by AIFeature base class.
    """
    FEATURE_KEY = "document_summary"

    async def run(self, document_text: str, output_format: str = "bullets", **kwargs):
        """
        Summarise a document into presentation-ready content.

        Args:
            document_text: Raw text of the document
            output_format: 'bullets' | 'paragraph' | 'slide_lines'

        Returns:
            dict with summary content

        TODO: Implement using Groq (reuse _groq from ppt_service)
        """
        log.info(f"[PLACEHOLDER] Document summary requested ({len(document_text)} chars)")

        # TODO: Implement
        # from app.services.ai_generation.ppt_service import _groq
        # summary = _groq([{"role": "user", "content": f"Summarise:\n{document_text[:8000]}"}])
        # return {"success": True, "summary": summary}

        return {
            "success": False,
            "message": "Document summarisation coming soon.",
            "feature": self.FEATURE_KEY,
        }
