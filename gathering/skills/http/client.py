"""HTTP client skill for making API requests."""

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from gathering.skills.base import BaseSkill, SkillResponse


@dataclass
class HTTPConfig:
    """Configuration for HTTP skill security."""

    # Allowed URL patterns (regex)
    allowed_patterns: list[str] = field(default_factory=lambda: [
        r"^https?://.*",  # Allow all HTTP/HTTPS by default
    ])

    # Blocked URL patterns
    blocked_patterns: list[str] = field(default_factory=lambda: [
        r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)",  # Block localhost
        r"^https?://192\.168\.",  # Block private networks
        r"^https?://10\.",
        r"^https?://172\.(1[6-9]|2[0-9]|3[01])\.",
        r"^file://",  # Block file protocol
    ])

    # Request timeout in seconds
    timeout: float = 30.0

    # Maximum response size in bytes (10 MB)
    max_response_size: int = 10 * 1024 * 1024

    # Default headers
    default_headers: dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "GatheRing-Agent/1.0",
    })

    # Allow following redirects
    follow_redirects: bool = True
    max_redirects: int = 5


class HTTPSkill(BaseSkill):
    """Skill for making HTTP requests and API calls."""

    name = "http"
    description = "Make HTTP requests and interact with REST APIs"
    version = "1.0.0"

    def __init__(self, config: HTTPConfig | dict | None = None):
        super().__init__(config if isinstance(config, dict) else None)
        self.http_config = config if isinstance(config, HTTPConfig) else HTTPConfig()

    def get_tools_definition(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "http_get",
                "description": "Make an HTTP GET request to retrieve data from a URL",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to request"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional headers to include",
                            "additionalProperties": {"type": "string"}
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters to add to URL",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "http_post",
                "description": "Make an HTTP POST request to send data to a URL",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to request"
                        },
                        "data": {
                            "type": "object",
                            "description": "JSON data to send in request body"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional headers to include",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "http_put",
                "description": "Make an HTTP PUT request to update a resource",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to request"
                        },
                        "data": {
                            "type": "object",
                            "description": "JSON data to send in request body"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional headers to include",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "http_delete",
                "description": "Make an HTTP DELETE request to remove a resource",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to request"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional headers to include",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "http_request",
                "description": "Make a custom HTTP request with any method",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
                        },
                        "url": {
                            "type": "string",
                            "description": "The URL to request"
                        },
                        "data": {
                            "type": "object",
                            "description": "JSON data to send in request body"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional headers to include",
                            "additionalProperties": {"type": "string"}
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["method", "url"]
                }
            },
            {
                "name": "api_call",
                "description": "Make a REST API call with authentication support",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "base_url": {
                            "type": "string",
                            "description": "Base URL of the API"
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "API endpoint path"
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                            "default": "GET"
                        },
                        "data": {
                            "type": "object",
                            "description": "Request body data"
                        },
                        "auth_type": {
                            "type": "string",
                            "description": "Authentication type",
                            "enum": ["none", "bearer", "basic", "api_key"],
                            "default": "none"
                        },
                        "auth_value": {
                            "type": "string",
                            "description": "Authentication value (token, user:pass, or api key)"
                        },
                        "api_key_header": {
                            "type": "string",
                            "description": "Header name for API key auth",
                            "default": "X-API-Key"
                        }
                    },
                    "required": ["base_url", "endpoint"]
                }
            },
            {
                "name": "parse_json",
                "description": "Parse a JSON string into a structured object",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "json_string": {
                            "type": "string",
                            "description": "JSON string to parse"
                        },
                        "extract_path": {
                            "type": "string",
                            "description": "Optional JSON path to extract (e.g., 'data.items[0].name')"
                        }
                    },
                    "required": ["json_string"]
                }
            },
            {
                "name": "build_url",
                "description": "Build a URL with query parameters",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "base_url": {
                            "type": "string",
                            "description": "Base URL"
                        },
                        "path": {
                            "type": "string",
                            "description": "URL path to append"
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["base_url"]
                }
            }
        ]

    def _validate_url(self, url: str) -> tuple[bool, str]:
        """Validate URL against security rules."""
        # Check blocked patterns first
        for pattern in self.http_config.blocked_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return False, f"URL blocked by security policy: {pattern}"

        # Check allowed patterns
        for pattern in self.http_config.allowed_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True, ""

        return False, "URL does not match any allowed pattern"

    def _make_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make an HTTP request with security checks."""
        # Validate URL
        is_valid, error = self._validate_url(url)
        if not is_valid:
            return {"success": False, "error": error}

        # Merge headers
        request_headers = {**self.http_config.default_headers}
        if headers:
            request_headers.update(headers)

        # Add content-type for JSON data
        if data and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"

        try:
            with httpx.Client(
                timeout=self.http_config.timeout,
                follow_redirects=self.http_config.follow_redirects,
                max_redirects=self.http_config.max_redirects
            ) as client:
                response = client.request(
                    method=method.upper(),
                    url=url,
                    headers=request_headers,
                    params=params,
                    json=data if data else None
                )

                # Check response size
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.http_config.max_response_size:
                    return {
                        "success": False,
                        "error": f"Response too large: {content_length} bytes"
                    }

                # Parse response
                result = {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }

                # Try to parse as JSON
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        result["data"] = response.json()
                    except json.JSONDecodeError:
                        result["text"] = response.text[:10000]  # Limit text size
                else:
                    result["text"] = response.text[:10000]

                return result

        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _extract_json_path(self, data: Any, path: str) -> Any:
        """Extract value from nested JSON using dot notation."""
        parts = path.replace("[", ".").replace("]", "").split(".")
        current = data

        for part in parts:
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute an HTTP tool."""

        if tool_name == "http_get":
            return self._make_request(
                "GET",
                tool_input["url"],
                headers=tool_input.get("headers"),
                params=tool_input.get("params")
            )

        elif tool_name == "http_post":
            return self._make_request(
                "POST",
                tool_input["url"],
                headers=tool_input.get("headers"),
                data=tool_input.get("data")
            )

        elif tool_name == "http_put":
            return self._make_request(
                "PUT",
                tool_input["url"],
                headers=tool_input.get("headers"),
                data=tool_input.get("data")
            )

        elif tool_name == "http_delete":
            return self._make_request(
                "DELETE",
                tool_input["url"],
                headers=tool_input.get("headers")
            )

        elif tool_name == "http_request":
            return self._make_request(
                tool_input["method"],
                tool_input["url"],
                headers=tool_input.get("headers"),
                params=tool_input.get("params"),
                data=tool_input.get("data")
            )

        elif tool_name == "api_call":
            base_url = tool_input["base_url"].rstrip("/")
            endpoint = tool_input["endpoint"].lstrip("/")
            url = f"{base_url}/{endpoint}"

            method = tool_input.get("method", "GET")
            headers = {}

            # Handle authentication
            auth_type = tool_input.get("auth_type", "none")
            auth_value = tool_input.get("auth_value", "")

            if auth_type == "bearer" and auth_value:
                headers["Authorization"] = f"Bearer {auth_value}"
            elif auth_type == "basic" and auth_value:
                import base64
                encoded = base64.b64encode(auth_value.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
            elif auth_type == "api_key" and auth_value:
                header_name = tool_input.get("api_key_header", "X-API-Key")
                headers[header_name] = auth_value

            return self._make_request(
                method,
                url,
                headers=headers,
                data=tool_input.get("data")
            )

        elif tool_name == "parse_json":
            try:
                data = json.loads(tool_input["json_string"])

                if "extract_path" in tool_input:
                    extracted = self._extract_json_path(data, tool_input["extract_path"])
                    return {"success": True, "data": extracted}

                return {"success": True, "data": data}

            except json.JSONDecodeError as e:
                return {"success": False, "error": f"Invalid JSON: {str(e)}"}

        elif tool_name == "build_url":
            base = tool_input["base_url"].rstrip("/")
            path = tool_input.get("path", "").lstrip("/")
            params = tool_input.get("params", {})

            url = f"{base}/{path}" if path else base

            if params:
                url = f"{url}?{urlencode(params)}"

            return {"success": True, "url": url}

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
