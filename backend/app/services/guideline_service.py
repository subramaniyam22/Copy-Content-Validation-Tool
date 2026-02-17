"""Guideline service — upload, parse, version, and manage guideline sets."""
import hashlib
from typing import Optional

from app.utils.file_extractors.pdf import extract_text_from_pdf
from app.utils.file_extractors.docx_ext import extract_text_from_docx
from app.utils.file_extractors.xlsx import extract_text_from_xlsx
from app.utils.file_extractors.csv_ext import extract_text_from_csv
from app.utils.file_extractors.txt import extract_text_from_txt
from app.utils.logging import logger


class GuidelineService:
    """Parse uploaded guideline files and extract text."""

    EXTRACTORS = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".xlsx": extract_text_from_xlsx,
        ".csv": extract_text_from_csv,
        ".txt": extract_text_from_txt,
    }

    def extract_text_from_files(self, files: list[dict]) -> tuple[str, str, list[dict]]:
        """
        Extract text from uploaded files.
        
        Args:
            files: list of {filename, content_bytes}
            
        Returns:
            (combined_text, text_hash, file_manifest)
        """
        all_text = []
        manifest = []

        for f in files:
            filename = f["filename"]
            content = f["content_bytes"]
            ext = self._get_extension(filename)

            extractor = self.EXTRACTORS.get(ext)
            if not extractor:
                logger.warning(f"Unsupported file type: {ext} for {filename}")
                manifest.append({"filename": filename, "status": "unsupported", "ext": ext})
                continue

            try:
                text = extractor(content)
                all_text.append(f"=== {filename} ===\n{text}")
                manifest.append({
                    "filename": filename,
                    "status": "ok",
                    "ext": ext,
                    "chars": len(text),
                })
            except Exception as e:
                logger.error(f"Failed to extract text from {filename}: {e}")
                manifest.append({"filename": filename, "status": "error", "error": str(e)})

        combined = "\n\n".join(all_text)
        text_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        return combined, text_hash, manifest

    def _get_extension(self, filename: str) -> str:
        """Get lowercase file extension."""
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[-1].lower()
        return ''
