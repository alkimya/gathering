"""
Document content extraction utilities.

Supports: Markdown, CSV, PDF, TXT
"""

import csv
import io
from pathlib import Path
from typing import Optional, Tuple

# Optional PDF support
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class DocumentExtractor:
    """Extract text content from various document formats."""

    SUPPORTED_EXTENSIONS = {'.md', '.markdown', '.txt', '.csv', '.pdf'}
    SUPPORTED_MIMETYPES = {
        'text/plain': 'txt',
        'text/markdown': 'md',
        'text/csv': 'csv',
        'application/pdf': 'pdf',
        'application/octet-stream': None,  # Detect from extension
    }

    @classmethod
    def is_supported(cls, filename: str, content_type: Optional[str] = None) -> bool:
        """Check if file format is supported."""
        ext = Path(filename).suffix.lower()
        if ext in cls.SUPPORTED_EXTENSIONS:
            return True
        if content_type and content_type in cls.SUPPORTED_MIMETYPES:
            return True
        return False

    @classmethod
    def get_format(cls, filename: str, content_type: Optional[str] = None) -> Optional[str]:
        """Determine document format from filename or content type."""
        ext = Path(filename).suffix.lower()

        if ext == '.pdf':
            return 'pdf'
        elif ext in {'.md', '.markdown'}:
            return 'markdown'
        elif ext == '.csv':
            return 'csv'
        elif ext == '.txt':
            return 'txt'

        # Fallback to content type
        if content_type:
            fmt = cls.SUPPORTED_MIMETYPES.get(content_type)
            if fmt:
                return fmt

        return None

    @classmethod
    def extract(
        cls,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        Extract text content from document.

        Returns:
            Tuple of (extracted_text, metadata)
        """
        fmt = cls.get_format(filename, content_type)

        if fmt == 'pdf':
            return cls._extract_pdf(content, filename)
        elif fmt == 'csv':
            return cls._extract_csv(content, filename)
        elif fmt in {'markdown', 'md'}:
            return cls._extract_markdown(content, filename)
        elif fmt == 'txt':
            return cls._extract_text(content, filename)
        else:
            raise ValueError(f"Unsupported document format: {filename}")

    @classmethod
    def _extract_text(cls, content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract plain text."""
        text = content.decode('utf-8', errors='replace')
        return text, {
            'format': 'txt',
            'filename': filename,
            'char_count': len(text),
            'line_count': text.count('\n') + 1,
        }

    @classmethod
    def _extract_markdown(cls, content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract markdown content (kept as-is for now)."""
        text = content.decode('utf-8', errors='replace')

        # Count headers for metadata
        headers = [line for line in text.split('\n') if line.startswith('#')]

        return text, {
            'format': 'markdown',
            'filename': filename,
            'char_count': len(text),
            'line_count': text.count('\n') + 1,
            'header_count': len(headers),
        }

    @classmethod
    def _extract_csv(cls, content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract CSV as structured text."""
        text = content.decode('utf-8', errors='replace')
        reader = csv.reader(io.StringIO(text))

        rows = list(reader)
        if not rows:
            return "", {'format': 'csv', 'filename': filename, 'row_count': 0}

        # First row as headers
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []

        # Convert to readable format
        output_lines = []
        for row in data_rows:
            row_text = ", ".join(
                f"{headers[i] if i < len(headers) else f'col{i}'}: {val}"
                for i, val in enumerate(row)
                if val.strip()
            )
            if row_text:
                output_lines.append(row_text)

        extracted = "\n".join(output_lines)

        return extracted, {
            'format': 'csv',
            'filename': filename,
            'row_count': len(rows),
            'column_count': len(headers),
            'headers': headers,
        }

    @classmethod
    def _extract_pdf(cls, content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract PDF text content."""
        if not HAS_PYPDF:
            raise ValueError(
                "PDF support requires pypdf. Install with: pip install pypdf"
            )

        pdf_file = io.BytesIO(content)
        reader = pypdf.PdfReader(pdf_file)

        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        extracted = "\n\n---\n\n".join(pages_text)

        return extracted, {
            'format': 'pdf',
            'filename': filename,
            'page_count': len(reader.pages),
            'char_count': len(extracted),
        }


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200
) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: The text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks

    Returns:
        List of chunk dicts with 'content', 'start', 'end' keys
    """
    if len(text) <= chunk_size:
        return [{'content': text, 'start': 0, 'end': len(text), 'index': 0}]

    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at sentence or paragraph boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind('\n\n', start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in ['. ', '.\n', '! ', '? ']:
                    sent_break = text.rfind(sep, start, end)
                    if sent_break > start + chunk_size // 2:
                        end = sent_break + len(sep)
                        break

        chunks.append({
            'content': text[start:end].strip(),
            'start': start,
            'end': end,
            'index': index,
        })

        index += 1
        start = end - overlap if end < len(text) else len(text)

    return chunks
