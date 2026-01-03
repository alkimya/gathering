"""
Web Scraper Skill - Advanced content extraction and parsing.
"""

import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin

import httpx

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class WebScraperSkill(BaseSkill):
    """
    Advanced web scraping and content extraction.

    Tools:
    - extract_links: Extract all links from a page
    - extract_images: Extract image URLs from a page
    - extract_metadata: Extract page metadata (title, description, etc.)
    - extract_structured: Extract structured data (JSON-LD, microdata)
    - extract_tables: Extract tables as structured data
    - extract_text_by_selector: Extract text using CSS-like selectors
    """

    name = "scraper"
    description = "Advanced web scraping and content extraction"
    version = "1.0.0"
    required_permissions = [SkillPermission.NETWORK]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None

    def initialize(self) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; GatheRing/1.0; +https://github.com/alkimya/gathering)"
            },
            follow_redirects=True,
        )
        self._initialized = True

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure async client is initialized."""
        if self._client is None:
            self.initialize()
        return self._client

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Return tool definitions."""
        return [
            {
                "name": "extract_links",
                "description": "Extract all links from a web page",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to scrape"},
                        "filter_pattern": {"type": "string", "description": "Regex to filter URLs"},
                        "include_text": {"type": "boolean", "default": True, "description": "Include link text"},
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "extract_images",
                "description": "Extract all image URLs from a web page",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to scrape"},
                        "include_alt": {"type": "boolean", "default": True, "description": "Include alt text"},
                        "min_size": {"type": "integer", "default": 0, "description": "Minimum image dimension"},
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "extract_metadata",
                "description": "Extract page metadata (title, description, Open Graph, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to analyze"},
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "extract_structured",
                "description": "Extract structured data (JSON-LD, Schema.org)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to analyze"},
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "extract_tables",
                "description": "Extract HTML tables as structured data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to scrape"},
                        "table_index": {"type": "integer", "description": "Specific table index (0-based)"},
                    },
                    "required": ["url"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Sync execution."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.execute_async(tool_name, tool_input))

    async def execute_async(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> SkillResponse:
        """Execute scraping tool."""
        start_time = datetime.utcnow()
        self.ensure_initialized()

        try:
            url = tool_input.get("url")
            if not url:
                return SkillResponse(
                    success=False,
                    message="URL is required",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            # Fetch the page
            client = await self._ensure_client()
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
            base_url = str(response.url)

            if tool_name == "extract_links":
                result = self._extract_links(
                    html, base_url,
                    filter_pattern=tool_input.get("filter_pattern"),
                    include_text=tool_input.get("include_text", True),
                )
            elif tool_name == "extract_images":
                result = self._extract_images(
                    html, base_url,
                    include_alt=tool_input.get("include_alt", True),
                )
            elif tool_name == "extract_metadata":
                result = self._extract_metadata(html, base_url)
            elif tool_name == "extract_structured":
                result = self._extract_structured(html)
            elif tool_name == "extract_tables":
                result = self._extract_tables(
                    html,
                    table_index=tool_input.get("table_index"),
                )
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return SkillResponse(
                success=True,
                message=f"Successfully extracted data from {url}",
                data=result,
                skill_name=self.name,
                tool_name=tool_name,
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return SkillResponse(
                success=False,
                message=f"Error: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
                duration_ms=duration,
            )

    def _extract_links(
        self, html: str, base_url: str,
        filter_pattern: Optional[str] = None,
        include_text: bool = True
    ) -> Dict[str, Any]:
        """Extract links from HTML."""
        pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        links = []
        seen_urls = set()

        for href, text in matches:
            # Resolve relative URLs
            full_url = urljoin(base_url, href)

            # Skip duplicates, anchors, javascript
            if full_url in seen_urls:
                continue
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            # Apply filter
            if filter_pattern:
                if not re.search(filter_pattern, full_url):
                    continue

            seen_urls.add(full_url)
            link_data = {"url": full_url}
            if include_text:
                link_data["text"] = re.sub(r'<[^>]+>', '', text).strip()

            links.append(link_data)

        return {
            "url": base_url,
            "total_links": len(links),
            "links": links,
        }

    def _extract_images(
        self, html: str, base_url: str,
        include_alt: bool = True
    ) -> Dict[str, Any]:
        """Extract images from HTML."""
        pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        alt_pattern = r'alt=["\']([^"\']*)["\']'

        images = []
        seen_urls = set()

        for match in re.finditer(pattern, html, re.IGNORECASE):
            tag = match.group(0)
            src = match.group(1)

            # Resolve relative URLs
            full_url = urljoin(base_url, src)

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            img_data = {"url": full_url}

            if include_alt:
                alt_match = re.search(alt_pattern, tag, re.IGNORECASE)
                img_data["alt"] = alt_match.group(1) if alt_match else ""

            images.append(img_data)

        return {
            "url": base_url,
            "total_images": len(images),
            "images": images,
        }

    def _extract_metadata(self, html: str, base_url: str) -> Dict[str, Any]:
        """Extract page metadata."""
        metadata = {
            "url": base_url,
            "title": None,
            "description": None,
            "keywords": None,
            "canonical": None,
            "language": None,
            "og": {},
            "twitter": {},
        }

        # Title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # Meta tags
        meta_pattern = r'<meta[^>]*(?:name|property)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']*)["\'][^>]*>'
        meta_pattern_rev = r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']([^"\']+)["\'][^>]*>'

        for match in re.finditer(meta_pattern, html, re.IGNORECASE):
            name, content = match.group(1).lower(), match.group(2)
            self._process_meta(metadata, name, content)

        for match in re.finditer(meta_pattern_rev, html, re.IGNORECASE):
            content, name = match.group(1), match.group(2).lower()
            self._process_meta(metadata, name, content)

        # Canonical URL
        canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if canonical_match:
            metadata["canonical"] = canonical_match.group(1)

        # Language
        lang_match = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if lang_match:
            metadata["language"] = lang_match.group(1)

        return metadata

    def _process_meta(self, metadata: dict, name: str, content: str):
        """Process a meta tag."""
        if name == "description":
            metadata["description"] = content
        elif name == "keywords":
            metadata["keywords"] = [k.strip() for k in content.split(",")]
        elif name.startswith("og:"):
            metadata["og"][name[3:]] = content
        elif name.startswith("twitter:"):
            metadata["twitter"][name[8:]] = content

    def _extract_structured(self, html: str) -> Dict[str, Any]:
        """Extract JSON-LD structured data."""
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        structured_data = []
        for match in matches:
            try:
                data = json.loads(match.strip())
                structured_data.append(data)
            except json.JSONDecodeError:
                continue

        return {
            "count": len(structured_data),
            "data": structured_data,
        }

    def _extract_tables(
        self, html: str,
        table_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """Extract HTML tables."""
        table_pattern = r'<table[^>]*>(.*?)</table>'
        tables = re.findall(table_pattern, html, re.DOTALL | re.IGNORECASE)

        if table_index is not None:
            if 0 <= table_index < len(tables):
                tables = [tables[table_index]]
            else:
                return {"error": f"Table index {table_index} not found", "total_tables": len(tables)}

        result = []
        for i, table_html in enumerate(tables):
            rows = []
            headers = []

            # Extract headers
            th_pattern = r'<th[^>]*>(.*?)</th>'
            headers = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(th_pattern, table_html, re.DOTALL | re.IGNORECASE)]

            # Extract rows
            tr_pattern = r'<tr[^>]*>(.*?)</tr>'
            td_pattern = r'<td[^>]*>(.*?)</td>'

            for tr in re.findall(tr_pattern, table_html, re.DOTALL | re.IGNORECASE):
                cells = [re.sub(r'<[^>]+>', '', td).strip() for td in re.findall(td_pattern, tr, re.DOTALL | re.IGNORECASE)]
                if cells:
                    if headers and len(cells) == len(headers):
                        rows.append(dict(zip(headers, cells)))
                    else:
                        rows.append(cells)

            result.append({
                "index": i,
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
            })

        return {
            "total_tables": len(result),
            "tables": result,
        }

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
