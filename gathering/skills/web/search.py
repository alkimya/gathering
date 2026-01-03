"""
Web Search Skill - Multi-engine web search capabilities.
"""

import re
import urllib.parse
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import httpx

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str
    published_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "published_date": self.published_date,
        }


class WebSearchSkill(BaseSkill):
    """
    Web search skill using multiple search engines.

    Supports:
    - DuckDuckGo (free, no API key)
    - Brave Search (API key optional)
    - Wikipedia (free)
    - News search via various APIs

    Tools:
    - web_search: General web search
    - wikipedia_search: Search Wikipedia
    - news_search: Search news articles
    - fetch_url: Fetch a URL and extract text
    """

    name = "web"
    description = "Web search and content retrieval"
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
        """Return tool definitions for LLM."""
        return [
            {
                "name": "web_search",
                "description": "Search the web for information. Returns titles, URLs, and snippets from search results.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default: 10, max: 30)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 30
                        },
                        "region": {
                            "type": "string",
                            "description": "Region code (e.g., 'fr-fr', 'en-us')",
                            "default": "wt-wt"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "wikipedia_search",
                "description": "Search Wikipedia for articles. Returns article titles and summaries.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "language": {
                            "type": "string",
                            "description": "Wikipedia language code (e.g., 'en', 'fr', 'de')",
                            "default": "en"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results (default: 5)",
                            "default": 5,
                            "maximum": 20
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "wikipedia_article",
                "description": "Get the full content of a Wikipedia article.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact article title"
                        },
                        "language": {
                            "type": "string",
                            "description": "Wikipedia language code",
                            "default": "en"
                        },
                        "sections": {
                            "type": "boolean",
                            "description": "Include section breakdown",
                            "default": False
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "fetch_url",
                "description": "Fetch a web page and extract its text content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch"
                        },
                        "extract_mode": {
                            "type": "string",
                            "enum": ["text", "html", "markdown"],
                            "description": "Content extraction mode",
                            "default": "text"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum content length in characters",
                            "default": 50000
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "news_search",
                "description": "Search for recent news articles on a topic.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "News search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 10,
                            "maximum": 50
                        },
                        "time_range": {
                            "type": "string",
                            "enum": ["day", "week", "month"],
                            "description": "Time range for news",
                            "default": "week"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Sync execution - wraps async."""
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
        """Execute a web search tool."""
        start_time = datetime.utcnow()
        self.ensure_initialized()

        try:
            if tool_name == "web_search":
                result = await self._web_search(
                    query=tool_input["query"],
                    num_results=tool_input.get("num_results", 10),
                    region=tool_input.get("region", "wt-wt"),
                )
            elif tool_name == "wikipedia_search":
                result = await self._wikipedia_search(
                    query=tool_input["query"],
                    language=tool_input.get("language", "en"),
                    num_results=tool_input.get("num_results", 5),
                )
            elif tool_name == "wikipedia_article":
                result = await self._wikipedia_article(
                    title=tool_input["title"],
                    language=tool_input.get("language", "en"),
                    sections=tool_input.get("sections", False),
                )
            elif tool_name == "fetch_url":
                result = await self._fetch_url(
                    url=tool_input["url"],
                    extract_mode=tool_input.get("extract_mode", "text"),
                    max_length=tool_input.get("max_length", 50000),
                )
            elif tool_name == "news_search":
                result = await self._news_search(
                    query=tool_input["query"],
                    num_results=tool_input.get("num_results", 10),
                    time_range=tool_input.get("time_range", "week"),
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
                message=f"Successfully executed {tool_name}",
                data=result,
                skill_name=self.name,
                tool_name=tool_name,
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return SkillResponse(
                success=False,
                message=f"Error executing {tool_name}: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
                duration_ms=duration,
            )

    async def _web_search(
        self, query: str, num_results: int = 10, region: str = "wt-wt"
    ) -> Dict[str, Any]:
        """
        Search using DuckDuckGo HTML interface.
        No API key required.
        """
        client = await self._ensure_client()

        # DuckDuckGo HTML search
        url = "https://html.duckduckgo.com/html/"
        data = {
            "q": query,
            "kl": region,
        }

        response = await client.post(url, data=data)
        response.raise_for_status()

        # Parse results from HTML
        results = self._parse_ddg_html(response.text, num_results)

        return {
            "query": query,
            "num_results": len(results),
            "results": [r.to_dict() for r in results],
        }

    def _parse_ddg_html(self, html: str, max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Simple regex parsing for DDG results
        # Look for result blocks
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'

        links = re.findall(result_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            # Decode DDG redirect URL
            if url.startswith("//duckduckgo.com/l/?uddg="):
                url = urllib.parse.unquote(url.split("uddg=")[1].split("&")[0])

            results.append(SearchResult(
                title=title.strip(),
                url=url,
                snippet=snippet.strip(),
                source="duckduckgo",
            ))

        return results

    async def _wikipedia_search(
        self, query: str, language: str = "en", num_results: int = 5
    ) -> Dict[str, Any]:
        """Search Wikipedia API."""
        client = await self._ensure_client()

        url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": num_results,
            "format": "json",
            "utf8": 1,
        }

        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("query", {}).get("search", []):
            # Clean HTML from snippet
            snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
            results.append({
                "title": item.get("title"),
                "snippet": snippet,
                "page_id": item.get("pageid"),
                "url": f"https://{language}.wikipedia.org/wiki/{urllib.parse.quote(item.get('title', '').replace(' ', '_'))}",
                "word_count": item.get("wordcount", 0),
            })

        return {
            "query": query,
            "language": language,
            "num_results": len(results),
            "results": results,
        }

    async def _wikipedia_article(
        self, title: str, language: str = "en", sections: bool = False
    ) -> Dict[str, Any]:
        """Get Wikipedia article content."""
        client = await self._ensure_client()

        url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "exintro": not sections,  # Full article if sections requested
            "explaintext": True,
            "inprop": "url",
            "format": "json",
            "utf8": 1,
        }

        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return {"error": "Article not found", "title": title}

        page = list(pages.values())[0]
        if "missing" in page:
            return {"error": "Article not found", "title": title}

        return {
            "title": page.get("title"),
            "page_id": page.get("pageid"),
            "url": page.get("fullurl"),
            "content": page.get("extract", ""),
            "length": len(page.get("extract", "")),
        }

    async def _fetch_url(
        self, url: str, extract_mode: str = "text", max_length: int = 50000
    ) -> Dict[str, Any]:
        """Fetch a URL and extract content."""
        client = await self._ensure_client()

        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        html = response.text

        if extract_mode == "html":
            content = html[:max_length]
        elif extract_mode == "markdown":
            content = self._html_to_markdown(html)[:max_length]
        else:  # text
            content = self._extract_text(html)[:max_length]

        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": content_type,
            "content": content,
            "length": len(content),
            "truncated": len(content) >= max_length,
        }

    def _extract_text(self, html: str) -> str:
        """Extract text from HTML."""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)

        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown (basic)."""
        # Remove script/style
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert headers
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert links
        html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert bold/italic
        html = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert lists
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert paragraphs
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', html)

        # Clean whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    async def _news_search(
        self, query: str, num_results: int = 10, time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Search for news using DuckDuckGo news.
        """
        client = await self._ensure_client()

        # Map time range to DDG format
        time_map = {
            "day": "d",
            "week": "w",
            "month": "m",
        }
        df = time_map.get(time_range, "w")

        url = "https://html.duckduckgo.com/html/"
        data = {
            "q": query,
            "iar": "news",
            "df": df,
        }

        response = await client.post(url, data=data)
        response.raise_for_status()

        results = self._parse_ddg_html(response.text, num_results)

        return {
            "query": query,
            "time_range": time_range,
            "num_results": len(results),
            "results": [r.to_dict() for r in results],
        }

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
