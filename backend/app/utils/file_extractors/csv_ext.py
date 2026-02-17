"""CSV text extraction."""
import csv
from io import BytesIO, StringIO


def extract_text_from_csv(file_bytes: bytes) -> str:
    """Extract text content from a CSV file."""
    text = file_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(StringIO(text))
    lines = []
    for row in reader:
        cells = [cell.strip() for cell in row if cell.strip()]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)
