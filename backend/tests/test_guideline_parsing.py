"""Tests for guideline parsing — file extractors."""
import os
import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestTxtExtractor:
    def test_extracts_text(self):
        from app.utils.file_extractors.txt import extract_text_from_txt
        with open(os.path.join(FIXTURES_DIR, 'sample_guidelines.txt'), 'rb') as f:
            content = f.read()
        text = extract_text_from_txt(content)
        assert "Brand Voice Guidelines" in text
        assert "click here" in text
        assert "active voice" in text

    def test_returns_string(self):
        from app.utils.file_extractors.txt import extract_text_from_txt
        with open(os.path.join(FIXTURES_DIR, 'sample_guidelines.txt'), 'rb') as f:
            content = f.read()
        text = extract_text_from_txt(content)
        assert isinstance(text, str)
        assert len(text) > 0


class TestCsvExtractor:
    def test_csv_extraction(self, tmp_path):
        from app.utils.file_extractors.csv_ext import extract_text_from_csv
        csv_content = b"Name,Value\nRule1,Do not use jargon\nRule2,Use active voice\n"
        text = extract_text_from_csv(csv_content)
        assert "Rule1" in text
        assert "jargon" in text
        assert "active voice" in text


class TestGuidelineService:
    def test_extract_from_txt_file(self):
        from app.services.guideline_service import GuidelineService
        svc = GuidelineService()
        with open(os.path.join(FIXTURES_DIR, 'sample_guidelines.txt'), 'rb') as f:
            content = f.read()

        files = [{"filename": "sample_guidelines.txt", "content_bytes": content}]
        combined_text, text_hash, manifest = svc.extract_text_from_files(files)

        assert len(combined_text) > 0
        assert len(text_hash) == 64  # SHA-256 hex
        assert len(manifest) == 1
        assert manifest[0]["filename"] == "sample_guidelines.txt"
        assert manifest[0]["status"] == "ok"

    def test_unknown_extension_skipped(self):
        from app.services.guideline_service import GuidelineService
        svc = GuidelineService()
        files = [{"filename": "image.png", "content_bytes": b"\x89PNG"}]
        combined_text, text_hash, manifest = svc.extract_text_from_files(files)

        assert combined_text == ""
        assert len(manifest) == 1
        assert manifest[0]["status"] == "unsupported"

    def test_multiple_files(self):
        from app.services.guideline_service import GuidelineService
        svc = GuidelineService()

        with open(os.path.join(FIXTURES_DIR, 'sample_guidelines.txt'), 'rb') as f:
            content = f.read()

        files = [
            {"filename": "file1.txt", "content_bytes": content},
            {"filename": "file2.txt", "content_bytes": b"Extra guidelines here."},
        ]
        combined_text, text_hash, manifest = svc.extract_text_from_files(files)

        assert "Brand Voice" in combined_text
        assert "Extra guidelines" in combined_text
        assert len(manifest) == 2

    def test_empty_file_list(self):
        from app.services.guideline_service import GuidelineService
        svc = GuidelineService()
        combined_text, text_hash, manifest = svc.extract_text_from_files([])
        assert combined_text == ""
        assert len(manifest) == 0

    def test_get_extension(self):
        from app.services.guideline_service import GuidelineService
        svc = GuidelineService()
        assert svc._get_extension("my_doc.pdf") == ".pdf"
        assert svc._get_extension("report.DOCX") == ".docx"
        assert svc._get_extension("data.xlsx") == ".xlsx"
        assert svc._get_extension("noext") == ""
