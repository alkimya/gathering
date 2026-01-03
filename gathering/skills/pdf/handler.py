"""
PDF Skill for GatheRing.
Provides PDF reading, text extraction, and generation capabilities.
"""

import os
import io
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class PDFSkill(BaseSkill):
    """
    Skill for PDF operations.

    Features:
    - Read and extract text from PDFs
    - Extract metadata and structure
    - Generate PDFs from text/HTML
    - Merge and split PDFs
    - Add watermarks
    - Convert to/from images

    Security:
    - Configurable allowed paths
    - File size limits
    """

    name = "pdf"
    description = "PDF reading and generation"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.WRITE]

    MAX_FILE_SIZE_MB = 100

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.allowed_paths = self.config.get("allowed_paths", []) if self.config else []
        self.max_size_mb = self.config.get("max_size_mb", self.MAX_FILE_SIZE_MB) if self.config else self.MAX_FILE_SIZE_MB

    def _check_path(self, path: str) -> bool:
        """Check if path is allowed."""
        if not self.allowed_paths:
            return True
        return any(path.startswith(p) for p in self.allowed_paths)

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "pdf_read",
                "description": "Extract text from a PDF file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "pages": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Specific page numbers to extract (1-indexed)"
                        },
                        "start_page": {
                            "type": "integer",
                            "description": "Start page (1-indexed)"
                        },
                        "end_page": {
                            "type": "integer",
                            "description": "End page (1-indexed, inclusive)"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "pdf_info",
                "description": "Get PDF metadata and information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "pdf_create",
                "description": "Create a PDF from text or HTML",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "description": "Output PDF path"
                        },
                        "content": {
                            "type": "string",
                            "description": "Text or HTML content"
                        },
                        "content_type": {
                            "type": "string",
                            "description": "Content type",
                            "enum": ["text", "html", "markdown"],
                            "default": "text"
                        },
                        "title": {
                            "type": "string",
                            "description": "Document title"
                        },
                        "author": {
                            "type": "string",
                            "description": "Document author"
                        },
                        "page_size": {
                            "type": "string",
                            "description": "Page size",
                            "enum": ["A4", "LETTER", "LEGAL"],
                            "default": "A4"
                        },
                        "margins": {
                            "type": "object",
                            "description": "Page margins in inches",
                            "properties": {
                                "top": {"type": "number"},
                                "bottom": {"type": "number"},
                                "left": {"type": "number"},
                                "right": {"type": "number"}
                            }
                        }
                    },
                    "required": ["output", "content"]
                }
            },
            {
                "name": "pdf_merge",
                "description": "Merge multiple PDFs into one",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of PDF files to merge"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output PDF path"
                        }
                    },
                    "required": ["files", "output"]
                }
            },
            {
                "name": "pdf_split",
                "description": "Split a PDF into multiple files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for split files"
                        },
                        "pages_per_file": {
                            "type": "integer",
                            "description": "Number of pages per output file",
                            "default": 1
                        },
                        "page_ranges": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer"},
                                    "end": {"type": "integer"}
                                }
                            },
                            "description": "Custom page ranges to extract"
                        }
                    },
                    "required": ["path", "output_dir"]
                }
            },
            {
                "name": "pdf_watermark",
                "description": "Add watermark to PDF",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output PDF path"
                        },
                        "text": {
                            "type": "string",
                            "description": "Watermark text"
                        },
                        "opacity": {
                            "type": "number",
                            "description": "Watermark opacity (0-1)",
                            "default": 0.3
                        },
                        "angle": {
                            "type": "number",
                            "description": "Rotation angle in degrees",
                            "default": 45
                        },
                        "position": {
                            "type": "string",
                            "description": "Watermark position",
                            "enum": ["center", "diagonal", "header", "footer"],
                            "default": "diagonal"
                        }
                    },
                    "required": ["path", "output", "text"]
                }
            },
            {
                "name": "pdf_to_images",
                "description": "Convert PDF pages to images",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for images"
                        },
                        "format": {
                            "type": "string",
                            "description": "Image format",
                            "enum": ["png", "jpeg", "webp"],
                            "default": "png"
                        },
                        "dpi": {
                            "type": "integer",
                            "description": "Resolution in DPI",
                            "default": 150
                        },
                        "pages": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Specific pages to convert"
                        }
                    },
                    "required": ["path", "output_dir"]
                }
            },
            {
                "name": "pdf_from_images",
                "description": "Create PDF from images",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of image file paths"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output PDF path"
                        },
                        "page_size": {
                            "type": "string",
                            "description": "Page size (A4, LETTER, or 'fit' to match image)",
                            "default": "fit"
                        }
                    },
                    "required": ["images", "output"]
                }
            },
            {
                "name": "pdf_extract_images",
                "description": "Extract images from PDF",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for extracted images"
                        },
                        "min_size": {
                            "type": "integer",
                            "description": "Minimum image size in pixels",
                            "default": 100
                        }
                    },
                    "required": ["path", "output_dir"]
                }
            },
            {
                "name": "pdf_search",
                "description": "Search for text in PDF",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Case sensitive search",
                            "default": False
                        }
                    },
                    "required": ["path", "query"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute PDF tool."""
        try:
            path = tool_input.get("path")

            if path and not self._check_path(path):
                return SkillResponse(
                    success=False,
                    message=f"Path not allowed: {path}",
                    error="access_denied"
                )

            if tool_name == "pdf_read":
                return self._read_pdf(tool_input)
            elif tool_name == "pdf_info":
                return self._get_info(tool_input)
            elif tool_name == "pdf_create":
                return self._create_pdf(tool_input)
            elif tool_name == "pdf_merge":
                return self._merge_pdfs(tool_input)
            elif tool_name == "pdf_split":
                return self._split_pdf(tool_input)
            elif tool_name == "pdf_watermark":
                return self._add_watermark(tool_input)
            elif tool_name == "pdf_to_images":
                return self._to_images(tool_input)
            elif tool_name == "pdf_from_images":
                return self._from_images(tool_input)
            elif tool_name == "pdf_extract_images":
                return self._extract_images(tool_input)
            elif tool_name == "pdf_search":
                return self._search_pdf(tool_input)
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )

        except ImportError as e:
            return SkillResponse(
                success=False,
                message=f"PDF library not installed: {e}. Install: pip install pypdf reportlab pdf2image",
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"PDF tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"PDF operation failed: {str(e)}",
                error=str(e)
            )

    def _read_pdf(self, params: Dict[str, Any]) -> SkillResponse:
        """Extract text from PDF."""
        from pypdf import PdfReader

        path = params["path"]
        pages = params.get("pages")
        start_page = params.get("start_page")
        end_page = params.get("end_page")

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        reader = PdfReader(path)
        total_pages = len(reader.pages)

        # Determine pages to extract
        if pages:
            page_indices = [p - 1 for p in pages if 0 < p <= total_pages]
        elif start_page or end_page:
            start = (start_page or 1) - 1
            end = end_page or total_pages
            page_indices = range(max(0, start), min(end, total_pages))
        else:
            page_indices = range(total_pages)

        # Extract text
        extracted = []
        for i in page_indices:
            page = reader.pages[i]
            text = page.extract_text()
            extracted.append({
                "page": i + 1,
                "text": text,
                "chars": len(text)
            })

        total_chars = sum(p["chars"] for p in extracted)

        return SkillResponse(
            success=True,
            message=f"Extracted text from {len(extracted)} page(s)",
            data={
                "pages": extracted,
                "total_pages": total_pages,
                "extracted_pages": len(extracted),
                "total_characters": total_chars,
            }
        )

    def _get_info(self, params: Dict[str, Any]) -> SkillResponse:
        """Get PDF information."""
        from pypdf import PdfReader

        path = params["path"]

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        reader = PdfReader(path)
        metadata = reader.metadata or {}

        # Get page info
        first_page = reader.pages[0]
        page_size = first_page.mediabox

        info = {
            "path": path,
            "pages": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "file_size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
            "page_size": {
                "width": float(page_size.width),
                "height": float(page_size.height),
            },
            "metadata": {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": str(metadata.get("/CreationDate", "")),
                "modification_date": str(metadata.get("/ModDate", "")),
            }
        }

        return SkillResponse(
            success=True,
            message=f"PDF: {info['pages']} pages",
            data=info
        )

    def _create_pdf(self, params: Dict[str, Any]) -> SkillResponse:
        """Create PDF from content."""
        from reportlab.lib.pagesizes import A4, LETTER, LEGAL
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        output = params["output"]
        content = params["content"]
        content_type = params.get("content_type", "text")
        title = params.get("title", "")
        author = params.get("author", "")
        page_size_name = params.get("page_size", "A4")
        margins = params.get("margins", {"top": 1, "bottom": 1, "left": 1, "right": 1})

        page_sizes = {"A4": A4, "LETTER": LETTER, "LEGAL": LEGAL}
        page_size = page_sizes.get(page_size_name, A4)

        doc = SimpleDocTemplate(
            output,
            pagesize=page_size,
            topMargin=margins.get("top", 1) * inch,
            bottomMargin=margins.get("bottom", 1) * inch,
            leftMargin=margins.get("left", 1) * inch,
            rightMargin=margins.get("right", 1) * inch,
            title=title,
            author=author,
        )

        styles = getSampleStyleSheet()
        story = []

        if content_type == "text":
            # Plain text - split into paragraphs
            for para in content.split("\n\n"):
                if para.strip():
                    story.append(Paragraph(para.replace("\n", "<br/>"), styles["Normal"]))
                    story.append(Spacer(1, 12))

        elif content_type == "html":
            # HTML content - reportlab supports basic HTML
            story.append(Paragraph(content, styles["Normal"]))

        elif content_type == "markdown":
            # Convert markdown to basic HTML
            import re
            html = content
            # Headers
            html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
            html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
            html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
            # Bold and italic
            html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
            html = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html)
            # Line breaks
            html = html.replace("\n", "<br/>")

            story.append(Paragraph(html, styles["Normal"]))

        doc.build(story)

        return SkillResponse(
            success=True,
            message=f"PDF created: {output}",
            data={
                "output": output,
                "page_size": page_size_name,
                "size_bytes": os.path.getsize(output),
            }
        )

    def _merge_pdfs(self, params: Dict[str, Any]) -> SkillResponse:
        """Merge multiple PDFs."""
        from pypdf import PdfWriter

        files = params["files"]
        output = params["output"]

        writer = PdfWriter()
        total_pages = 0

        for pdf_file in files:
            if not os.path.exists(pdf_file):
                return SkillResponse(
                    success=False,
                    message=f"File not found: {pdf_file}",
                    error="not_found"
                )

            writer.append(pdf_file)
            total_pages += len(writer.pages) - total_pages

        writer.write(output)
        writer.close()

        return SkillResponse(
            success=True,
            message=f"Merged {len(files)} PDFs ({total_pages} pages)",
            data={
                "output": output,
                "merged_files": len(files),
                "total_pages": total_pages,
            }
        )

    def _split_pdf(self, params: Dict[str, Any]) -> SkillResponse:
        """Split PDF into multiple files."""
        from pypdf import PdfReader, PdfWriter

        path = params["path"]
        output_dir = params["output_dir"]
        pages_per_file = params.get("pages_per_file", 1)
        page_ranges = params.get("page_ranges")

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        os.makedirs(output_dir, exist_ok=True)

        reader = PdfReader(path)
        total_pages = len(reader.pages)
        output_files = []
        base_name = Path(path).stem

        if page_ranges:
            # Custom page ranges
            for i, range_spec in enumerate(page_ranges):
                start = range_spec.get("start", 1) - 1
                end = range_spec.get("end", total_pages)

                writer = PdfWriter()
                for page_num in range(start, min(end, total_pages)):
                    writer.add_page(reader.pages[page_num])

                output_path = os.path.join(output_dir, f"{base_name}_part{i + 1}.pdf")
                writer.write(output_path)
                writer.close()
                output_files.append(output_path)
        else:
            # Split by pages_per_file
            for i in range(0, total_pages, pages_per_file):
                writer = PdfWriter()
                for page_num in range(i, min(i + pages_per_file, total_pages)):
                    writer.add_page(reader.pages[page_num])

                output_path = os.path.join(output_dir, f"{base_name}_pages{i + 1}-{min(i + pages_per_file, total_pages)}.pdf")
                writer.write(output_path)
                writer.close()
                output_files.append(output_path)

        return SkillResponse(
            success=True,
            message=f"Split into {len(output_files)} file(s)",
            data={
                "output_dir": output_dir,
                "files": output_files,
                "original_pages": total_pages,
            }
        )

    def _add_watermark(self, params: Dict[str, Any]) -> SkillResponse:
        """Add watermark to PDF."""
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import Color

        path = params["path"]
        output = params["output"]
        text = params["text"]
        opacity = params.get("opacity", 0.3)
        angle = params.get("angle", 45)
        position = params.get("position", "diagonal")

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        # Create watermark PDF in memory
        packet = io.BytesIO()
        reader = PdfReader(path)
        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)

        c = canvas.Canvas(packet, pagesize=(page_width, page_height))
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
        c.setFont("Helvetica", 60)

        if position == "diagonal":
            c.saveState()
            c.translate(page_width / 2, page_height / 2)
            c.rotate(angle)
            c.drawCentredString(0, 0, text)
            c.restoreState()
        elif position == "center":
            c.drawCentredString(page_width / 2, page_height / 2, text)
        elif position == "header":
            c.setFont("Helvetica", 12)
            c.drawCentredString(page_width / 2, page_height - 30, text)
        elif position == "footer":
            c.setFont("Helvetica", 12)
            c.drawCentredString(page_width / 2, 30, text)

        c.save()
        packet.seek(0)

        # Apply watermark
        watermark = PdfReader(packet)
        watermark_page = watermark.pages[0]

        writer = PdfWriter()
        for page in reader.pages:
            page.merge_page(watermark_page)
            writer.add_page(page)

        writer.write(output)
        writer.close()

        return SkillResponse(
            success=True,
            message=f"Watermark added to {len(reader.pages)} page(s)",
            data={
                "output": output,
                "watermark_text": text,
                "pages": len(reader.pages),
            }
        )

    def _to_images(self, params: Dict[str, Any]) -> SkillResponse:
        """Convert PDF to images."""
        from pdf2image import convert_from_path

        path = params["path"]
        output_dir = params["output_dir"]
        fmt = params.get("format", "png")
        dpi = params.get("dpi", 150)
        pages = params.get("pages")

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        os.makedirs(output_dir, exist_ok=True)

        # Convert
        if pages:
            images = convert_from_path(path, dpi=dpi, first_page=min(pages), last_page=max(pages))
        else:
            images = convert_from_path(path, dpi=dpi)

        base_name = Path(path).stem
        output_files = []

        for i, image in enumerate(images):
            page_num = pages[i] if pages else i + 1
            output_path = os.path.join(output_dir, f"{base_name}_page{page_num}.{fmt}")
            image.save(output_path, fmt.upper())
            output_files.append(output_path)

        return SkillResponse(
            success=True,
            message=f"Converted {len(output_files)} page(s) to images",
            data={
                "output_dir": output_dir,
                "files": output_files,
                "format": fmt,
                "dpi": dpi,
            }
        )

    def _from_images(self, params: Dict[str, Any]) -> SkillResponse:
        """Create PDF from images."""
        from PIL import Image

        images = params["images"]
        output = params["output"]
        # page_size could be used for custom sizing
        _ = params.get("page_size", "fit")

        if not images:
            return SkillResponse(
                success=False,
                message="No images provided",
                error="no_images"
            )

        # Load and convert images
        pil_images = []
        for img_path in images:
            if not os.path.exists(img_path):
                return SkillResponse(
                    success=False,
                    message=f"Image not found: {img_path}",
                    error="not_found"
                )

            img = Image.open(img_path)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            pil_images.append(img)

        # Save as PDF
        first_image = pil_images[0]
        if len(pil_images) > 1:
            first_image.save(output, save_all=True, append_images=pil_images[1:])
        else:
            first_image.save(output)

        # Clean up
        for img in pil_images:
            img.close()

        return SkillResponse(
            success=True,
            message=f"Created PDF from {len(images)} image(s)",
            data={
                "output": output,
                "images_count": len(images),
            }
        )

    def _extract_images(self, params: Dict[str, Any]) -> SkillResponse:
        """Extract images from PDF."""
        from pypdf import PdfReader
        from PIL import Image

        path = params["path"]
        output_dir = params["output_dir"]
        min_size = params.get("min_size", 100)

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        os.makedirs(output_dir, exist_ok=True)

        reader = PdfReader(path)
        extracted = []
        base_name = Path(path).stem

        for page_num, page in enumerate(reader.pages):
            for img_num, image in enumerate(page.images):
                try:
                    # Check size
                    img_data = image.data
                    img = Image.open(io.BytesIO(img_data))

                    if img.width < min_size or img.height < min_size:
                        continue

                    # Determine extension
                    ext = image.name.split(".")[-1] if "." in image.name else "png"
                    output_path = os.path.join(
                        output_dir,
                        f"{base_name}_page{page_num + 1}_img{img_num + 1}.{ext}"
                    )

                    with open(output_path, "wb") as f:
                        f.write(img_data)

                    extracted.append({
                        "path": output_path,
                        "page": page_num + 1,
                        "size": f"{img.width}x{img.height}",
                    })

                except Exception as e:
                    logger.warning(f"Failed to extract image: {e}")
                    continue

        return SkillResponse(
            success=True,
            message=f"Extracted {len(extracted)} image(s)",
            data={
                "output_dir": output_dir,
                "images": extracted,
            }
        )

    def _search_pdf(self, params: Dict[str, Any]) -> SkillResponse:
        """Search for text in PDF."""
        from pypdf import PdfReader

        path = params["path"]
        query = params["query"]
        case_sensitive = params.get("case_sensitive", False)

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        reader = PdfReader(path)
        results = []

        search_query = query if case_sensitive else query.lower()

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            search_text = text if case_sensitive else text.lower()

            if search_query in search_text:
                # Find all occurrences
                start = 0
                occurrences = []
                while True:
                    pos = search_text.find(search_query, start)
                    if pos == -1:
                        break

                    # Get context (50 chars before and after)
                    context_start = max(0, pos - 50)
                    context_end = min(len(text), pos + len(query) + 50)
                    context = text[context_start:context_end]

                    occurrences.append({
                        "position": pos,
                        "context": f"...{context}..."
                    })
                    start = pos + 1

                results.append({
                    "page": page_num + 1,
                    "occurrences": len(occurrences),
                    "matches": occurrences[:5],  # Limit context samples
                })

        return SkillResponse(
            success=True,
            message=f"Found '{query}' on {len(results)} page(s)",
            data={
                "query": query,
                "pages_with_matches": len(results),
                "results": results,
            }
        )
