"""Plain text extraction."""


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text content from a TXT file."""
    return file_bytes.decode("utf-8", errors="replace")
