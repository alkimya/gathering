"""
AI Skill for GatheRing.
Provides LLM calls, embeddings, vision, and audio capabilities.
"""

import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class AISkill(BaseSkill):
    """
    AI model operations skill.

    Provides tools for:
    - Calling various LLM providers (OpenAI, Anthropic, Ollama, DeepSeek)
    - Generating text embeddings for RAG
    - Vision/image analysis
    - Audio transcription
    - Text-to-speech
    - Summarization and translation
    """

    name = "ai"
    description = "AI model operations (LLM, embeddings, vision, audio)"
    version = "1.0.0"
    required_permissions = [SkillPermission.NETWORK, SkillPermission.EXECUTE]

    # Supported providers
    PROVIDERS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
            "embedding_models": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
            "env_key": "OPENAI_API_KEY",
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"],
            "env_key": "ANTHROPIC_API_KEY",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-coder"],
            "env_key": "DEEPSEEK_API_KEY",
        },
        "ollama": {
            "base_url": "http://localhost:11434/api",
            "models": ["llama3", "mistral", "codellama", "phi3", "gemma"],
            "local": True,
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "models": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "env_key": "GROQ_API_KEY",
        },
    }

    # Safety limits
    MAX_TOKENS = 16000
    MAX_PROMPT_LENGTH = 100000
    EMBEDDING_CACHE_SIZE = 1000

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.default_provider = config.get("default_provider", "openai") if config else "openai"
        self.default_model = config.get("default_model") if config else None
        self.api_keys = config.get("api_keys", {}) if config else {}
        self._embedding_cache: Dict[str, List[float]] = {}

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "ai_complete",
                "description": "Call an LLM to generate a completion/response",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "The prompt/message to send"},
                        "system": {"type": "string", "description": "System prompt (optional)"},
                        "provider": {
                            "type": "string",
                            "enum": list(self.PROVIDERS.keys()),
                            "description": "LLM provider",
                        },
                        "model": {"type": "string", "description": "Model name"},
                        "temperature": {"type": "number", "description": "Temperature (0-2)", "default": 0.7},
                        "max_tokens": {"type": "integer", "description": "Max tokens to generate", "default": 1000},
                        "json_mode": {"type": "boolean", "description": "Request JSON output", "default": False}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "ai_chat",
                "description": "Multi-turn chat conversation with an LLM",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                    "content": {"type": "string"}
                                }
                            },
                            "description": "Conversation messages"
                        },
                        "provider": {"type": "string", "enum": list(self.PROVIDERS.keys())},
                        "model": {"type": "string"},
                        "temperature": {"type": "number", "default": 0.7},
                        "max_tokens": {"type": "integer", "default": 1000}
                    },
                    "required": ["messages"]
                }
            },
            {
                "name": "ai_embed",
                "description": "Generate embeddings for text (for RAG/similarity search)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to embed"},
                        "texts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Multiple texts to embed (batch)"
                        },
                        "model": {
                            "type": "string",
                            "description": "Embedding model",
                            "default": "text-embedding-3-small"
                        },
                        "provider": {"type": "string", "default": "openai"}
                    },
                    "required": []
                }
            },
            {
                "name": "ai_vision",
                "description": "Analyze an image using a vision model",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to image file"},
                        "image_url": {"type": "string", "description": "URL of image"},
                        "image_base64": {"type": "string", "description": "Base64 encoded image"},
                        "prompt": {"type": "string", "description": "What to analyze/ask about the image"},
                        "provider": {"type": "string", "enum": ["openai", "anthropic"], "default": "openai"},
                        "model": {"type": "string", "description": "Vision model to use"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "ai_transcribe",
                "description": "Transcribe audio to text (speech-to-text)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "audio_path": {"type": "string", "description": "Path to audio file"},
                        "language": {"type": "string", "description": "Language code (e.g., 'en', 'fr')"},
                        "model": {"type": "string", "default": "whisper-1"},
                        "timestamps": {"type": "boolean", "description": "Include word timestamps", "default": False}
                    },
                    "required": ["audio_path"]
                }
            },
            {
                "name": "ai_speak",
                "description": "Convert text to speech (text-to-speech)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to convert to speech"},
                        "output_path": {"type": "string", "description": "Output audio file path"},
                        "voice": {
                            "type": "string",
                            "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                            "description": "Voice to use",
                            "default": "alloy"
                        },
                        "model": {"type": "string", "default": "tts-1"}
                    },
                    "required": ["text", "output_path"]
                }
            },
            {
                "name": "ai_summarize",
                "description": "Summarize text content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to summarize"},
                        "max_length": {"type": "integer", "description": "Max summary length in words", "default": 200},
                        "style": {
                            "type": "string",
                            "enum": ["brief", "detailed", "bullets", "executive"],
                            "description": "Summary style",
                            "default": "brief"
                        },
                        "provider": {"type": "string"},
                        "model": {"type": "string"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "ai_translate",
                "description": "Translate text between languages",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to translate"},
                        "target_language": {"type": "string", "description": "Target language (e.g., 'French', 'es', 'Japanese')"},
                        "source_language": {"type": "string", "description": "Source language (auto-detect if not specified)"},
                        "provider": {"type": "string"},
                        "model": {"type": "string"}
                    },
                    "required": ["text", "target_language"]
                }
            },
            {
                "name": "ai_extract",
                "description": "Extract structured data from text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to extract from"},
                        "schema": {
                            "type": "object",
                            "description": "JSON schema of data to extract"
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Simple list of fields to extract"
                        },
                        "provider": {"type": "string"},
                        "model": {"type": "string"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "ai_compare",
                "description": "Compare two texts for similarity",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text1": {"type": "string", "description": "First text"},
                        "text2": {"type": "string", "description": "Second text"},
                        "method": {
                            "type": "string",
                            "enum": ["embedding", "llm"],
                            "description": "Comparison method",
                            "default": "embedding"
                        }
                    },
                    "required": ["text1", "text2"]
                }
            },
            {
                "name": "ai_models",
                "description": "List available models for a provider",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "Provider name (or 'all')"}
                    },
                    "required": []
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute an AI tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "ai_complete": self._ai_complete,
                "ai_chat": self._ai_chat,
                "ai_embed": self._ai_embed,
                "ai_vision": self._ai_vision,
                "ai_transcribe": self._ai_transcribe,
                "ai_speak": self._ai_speak,
                "ai_summarize": self._ai_summarize,
                "ai_translate": self._ai_translate,
                "ai_extract": self._ai_extract,
                "ai_compare": self._ai_compare,
                "ai_models": self._ai_models,
            }

            if tool_name not in handlers:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            result = handlers[tool_name](tool_input)
            result.skill_name = self.name
            result.tool_name = tool_name
            result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return result

        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error executing {tool_name}: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
            )

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider."""
        if provider in self.api_keys:
            return self.api_keys[provider]

        provider_info = self.PROVIDERS.get(provider, {})
        env_key = provider_info.get("env_key")
        if env_key:
            return os.environ.get(env_key)

        return None

    def _ai_complete(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate LLM completion."""
        prompt = tool_input["prompt"]
        system = tool_input.get("system")
        provider = tool_input.get("provider", self.default_provider)
        model = tool_input.get("model", self.default_model)
        temperature = tool_input.get("temperature", 0.7)
        max_tokens = min(tool_input.get("max_tokens", 1000), self.MAX_TOKENS)
        json_mode = tool_input.get("json_mode", False)

        if len(prompt) > self.MAX_PROMPT_LENGTH:
            return SkillResponse(
                success=False,
                message=f"Prompt too long: {len(prompt)} chars (max {self.MAX_PROMPT_LENGTH})",
                error="prompt_too_long"
            )

        # Check provider
        if provider not in self.PROVIDERS:
            return SkillResponse(
                success=False,
                message=f"Unknown provider: {provider}",
                error="unknown_provider",
                data={"available_providers": list(self.PROVIDERS.keys())}
            )

        # Get API key
        api_key = self._get_api_key(provider)
        provider_info = self.PROVIDERS[provider]

        if not api_key and not provider_info.get("local"):
            return SkillResponse(
                success=False,
                message=f"No API key for {provider}. Set {provider_info.get('env_key', 'API_KEY')}",
                error="no_api_key"
            )

        # Default model
        if not model:
            model = provider_info["models"][0]

        # Build request based on provider
        if provider == "ollama":
            return self._call_ollama(prompt, system, model, temperature, max_tokens)
        elif provider == "anthropic":
            return self._call_anthropic(prompt, system, model, temperature, max_tokens, api_key)
        else:
            # OpenAI-compatible (openai, deepseek, groq)
            return self._call_openai_compatible(
                prompt, system, model, temperature, max_tokens,
                api_key, provider_info["base_url"], json_mode
            )

    def _call_openai_compatible(
        self, prompt: str, system: Optional[str], model: str,
        temperature: float, max_tokens: int, api_key: str,
        base_url: str, json_mode: bool = False
    ) -> SkillResponse:
        """Call OpenAI-compatible API."""
        import urllib.request
        import urllib.error

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))

            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})

            return SkillResponse(
                success=True,
                message=f"Generated {len(content)} chars",
                data={
                    "content": content,
                    "model": model,
                    "usage": usage,
                    "finish_reason": result["choices"][0].get("finish_reason"),
                }
            )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return SkillResponse(
                success=False,
                message=f"API error: {e.code}",
                error=error_body
            )

    def _call_anthropic(
        self, prompt: str, system: Optional[str], model: str,
        temperature: float, max_tokens: int, api_key: str
    ) -> SkillResponse:
        """Call Anthropic API."""
        import urllib.request
        import urllib.error

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))

            content = result["content"][0]["text"]
            usage = result.get("usage", {})

            return SkillResponse(
                success=True,
                message=f"Generated {len(content)} chars",
                data={
                    "content": content,
                    "model": model,
                    "usage": usage,
                    "stop_reason": result.get("stop_reason"),
                }
            )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return SkillResponse(
                success=False,
                message=f"API error: {e.code}",
                error=error_body
            )

    def _call_ollama(
        self, prompt: str, system: Optional[str], model: str,
        temperature: float, max_tokens: int
    ) -> SkillResponse:
        """Call Ollama local API."""
        import urllib.request
        import urllib.error

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        request = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))

            content = result.get("response", "")

            return SkillResponse(
                success=True,
                message=f"Generated {len(content)} chars (local)",
                data={
                    "content": content,
                    "model": model,
                    "eval_count": result.get("eval_count"),
                    "eval_duration": result.get("eval_duration"),
                }
            )

        except urllib.error.URLError as e:
            return SkillResponse(
                success=False,
                message="Ollama not running. Start with: ollama serve",
                error=str(e)
            )

    def _ai_chat(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Multi-turn chat."""
        messages = tool_input["messages"]
        provider = tool_input.get("provider", self.default_provider)
        model = tool_input.get("model", self.default_model)
        temperature = tool_input.get("temperature", 0.7)
        max_tokens = min(tool_input.get("max_tokens", 1000), self.MAX_TOKENS)

        api_key = self._get_api_key(provider)
        provider_info = self.PROVIDERS.get(provider, {})

        if not api_key and not provider_info.get("local"):
            return SkillResponse(
                success=False,
                message=f"No API key for {provider}",
                error="no_api_key"
            )

        if not model:
            model = provider_info.get("models", ["gpt-4o"])[0]

        # Use OpenAI-compatible for chat
        if provider == "ollama":
            # Convert to single prompt for Ollama
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            return self._call_ollama(prompt, None, model, temperature, max_tokens)

        # OpenAI-compatible chat
        import urllib.request

        base_url = provider_info.get("base_url", "https://api.openai.com/v1")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        if provider == "anthropic":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
            # Convert messages format for Anthropic
            system = next((m["content"] for m in messages if m["role"] == "system"), None)
            payload = {
                "model": model,
                "messages": [m for m in messages if m["role"] != "system"],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system:
                payload["system"] = system
            base_url = "https://api.anthropic.com/v1"
            data = json.dumps(payload).encode("utf-8")

        endpoint = f"{base_url}/messages" if provider == "anthropic" else f"{base_url}/chat/completions"

        request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))

            if provider == "anthropic":
                content = result["content"][0]["text"]
            else:
                content = result["choices"][0]["message"]["content"]

            return SkillResponse(
                success=True,
                message=f"Chat response: {len(content)} chars",
                data={
                    "content": content,
                    "model": model,
                    "messages_count": len(messages),
                }
            )

        except Exception as e:
            return SkillResponse(success=False, message=str(e), error=str(e))

    def _ai_embed(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate embeddings."""
        text = tool_input.get("text")
        texts = tool_input.get("texts", [])
        model = tool_input.get("model", "text-embedding-3-small")
        provider = tool_input.get("provider", "openai")

        if text:
            texts = [text]

        if not texts:
            return SkillResponse(
                success=False,
                message="No text provided for embedding",
                error="no_text"
            )

        api_key = self._get_api_key(provider)
        if not api_key:
            return SkillResponse(
                success=False,
                message=f"No API key for {provider}",
                error="no_api_key"
            )

        # Check cache
        embeddings = []
        texts_to_embed = []
        cache_keys = []

        for t in texts:
            cache_key = hashlib.md5(f"{model}:{t}".encode()).hexdigest()
            if cache_key in self._embedding_cache:
                embeddings.append(self._embedding_cache[cache_key])
            else:
                texts_to_embed.append(t)
                cache_keys.append(cache_key)

        # Call API for uncached
        if texts_to_embed:
            import urllib.request

            provider_info = self.PROVIDERS.get(provider, self.PROVIDERS["openai"])
            base_url = provider_info.get("base_url", "https://api.openai.com/v1")

            payload = {
                "model": model,
                "input": texts_to_embed,
            }

            data = json.dumps(payload).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            request = urllib.request.Request(
                f"{base_url}/embeddings",
                data=data,
                headers=headers,
                method="POST"
            )

            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))

                for i, item in enumerate(result["data"]):
                    embedding = item["embedding"]
                    embeddings.append(embedding)

                    # Cache
                    if len(self._embedding_cache) < self.EMBEDDING_CACHE_SIZE:
                        self._embedding_cache[cache_keys[i]] = embedding

            except Exception as e:
                return SkillResponse(success=False, message=str(e), error=str(e))

        return SkillResponse(
            success=True,
            message=f"Generated {len(embeddings)} embeddings ({len(embeddings[0])} dimensions)",
            data={
                "embeddings": embeddings if len(embeddings) > 1 else embeddings[0],
                "model": model,
                "dimensions": len(embeddings[0]) if embeddings else 0,
                "count": len(embeddings),
            }
        )

    def _ai_vision(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Analyze image with vision model."""
        image_path = tool_input.get("image_path")
        image_url = tool_input.get("image_url")
        image_base64 = tool_input.get("image_base64")
        prompt = tool_input["prompt"]
        provider = tool_input.get("provider", "openai")
        model = tool_input.get("model")

        # Get image content
        if image_path:
            path = Path(image_path)
            if not path.exists():
                return SkillResponse(success=False, message=f"Image not found: {image_path}", error="not_found")

            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Detect mime type
            suffix = path.suffix.lower()
            mime_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
            mime_type = mime_types.get(suffix, "image/jpeg")
            image_content = f"data:{mime_type};base64,{image_data}"

        elif image_base64:
            image_content = f"data:image/jpeg;base64,{image_base64}"
        elif image_url:
            image_content = image_url
        else:
            return SkillResponse(
                success=False,
                message="No image provided (use image_path, image_url, or image_base64)",
                error="no_image"
            )

        api_key = self._get_api_key(provider)
        if not api_key:
            return SkillResponse(success=False, message=f"No API key for {provider}", error="no_api_key")

        import urllib.request

        if provider == "anthropic":
            model = model or "claude-3-5-sonnet-20241022"

            # Extract base64 data
            if image_content.startswith("data:"):
                parts = image_content.split(",", 1)
                media_type = parts[0].split(":")[1].split(";")[0]
                data_b64 = parts[1]
            else:
                # URL - need to fetch
                return SkillResponse(
                    success=False,
                    message="Anthropic requires base64 image, not URL",
                    error="url_not_supported"
                )

            payload = {
                "model": model,
                "max_tokens": 1024,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": data_b64,
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            }

            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }

            request = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

        else:  # OpenAI
            model = model or "gpt-4o"

            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_content}}
                    ]
                }],
                "max_tokens": 1024,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))

            if provider == "anthropic":
                content = result["content"][0]["text"]
            else:
                content = result["choices"][0]["message"]["content"]

            return SkillResponse(
                success=True,
                message="Image analyzed",
                data={
                    "analysis": content,
                    "model": model,
                    "provider": provider,
                }
            )

        except Exception as e:
            return SkillResponse(success=False, message=str(e), error=str(e))

    def _ai_transcribe(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Transcribe audio."""
        audio_path = tool_input["audio_path"]
        language = tool_input.get("language")
        model = tool_input.get("model", "whisper-1")
        timestamps = tool_input.get("timestamps", False)

        path = Path(audio_path)
        if not path.exists():
            return SkillResponse(success=False, message=f"Audio file not found: {audio_path}", error="not_found")

        api_key = self._get_api_key("openai")
        if not api_key:
            return SkillResponse(success=False, message="No OpenAI API key for transcription", error="no_api_key")

        import urllib.request

        # Multipart form data
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

        with open(path, "rb") as f:
            audio_data = f.read()

        body_parts = []

        # File part
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{path.name}"'.encode())
        body_parts.append(b"Content-Type: audio/mpeg")
        body_parts.append(b"")
        body_parts.append(audio_data)

        # Model part
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"')
        body_parts.append(b"")
        body_parts.append(model.encode())

        # Language part
        if language:
            body_parts.append(f"--{boundary}".encode())
            body_parts.append(b'Content-Disposition: form-data; name="language"')
            body_parts.append(b"")
            body_parts.append(language.encode())

        # Response format
        if timestamps:
            body_parts.append(f"--{boundary}".encode())
            body_parts.append(b'Content-Disposition: form-data; name="response_format"')
            body_parts.append(b"")
            body_parts.append(b"verbose_json")

        body_parts.append(f"--{boundary}--".encode())

        body = b"\r\n".join(body_parts)

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {api_key}",
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/audio/transcriptions",
            data=body,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))

            if timestamps:
                return SkillResponse(
                    success=True,
                    message=f"Transcribed {result.get('duration', 0):.1f}s of audio",
                    data={
                        "text": result.get("text", ""),
                        "segments": result.get("segments", []),
                        "language": result.get("language"),
                        "duration": result.get("duration"),
                    }
                )
            else:
                text = result.get("text", result) if isinstance(result, dict) else result
                return SkillResponse(
                    success=True,
                    message=f"Transcribed audio",
                    data={"text": text}
                )

        except Exception as e:
            return SkillResponse(success=False, message=str(e), error=str(e))

    def _ai_speak(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Text to speech."""
        text = tool_input["text"]
        output_path = tool_input["output_path"]
        voice = tool_input.get("voice", "alloy")
        model = tool_input.get("model", "tts-1")

        api_key = self._get_api_key("openai")
        if not api_key:
            return SkillResponse(success=False, message="No OpenAI API key for TTS", error="no_api_key")

        import urllib.request

        payload = {
            "model": model,
            "input": text,
            "voice": voice,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                audio_data = response.read()

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

            with open(output, "wb") as f:
                f.write(audio_data)

            return SkillResponse(
                success=True,
                message=f"Generated speech: {output_path}",
                data={
                    "output_path": str(output),
                    "size_bytes": len(audio_data),
                    "voice": voice,
                    "model": model,
                }
            )

        except Exception as e:
            return SkillResponse(success=False, message=str(e), error=str(e))

    def _ai_summarize(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Summarize text."""
        text = tool_input["text"]
        max_length = tool_input.get("max_length", 200)
        style = tool_input.get("style", "brief")
        provider = tool_input.get("provider", self.default_provider)
        model = tool_input.get("model")

        style_prompts = {
            "brief": f"Summarize the following text in {max_length} words or less. Be concise.",
            "detailed": f"Provide a detailed summary of the following text in about {max_length} words.",
            "bullets": f"Summarize the following text as bullet points (max {max_length} words total).",
            "executive": f"Write an executive summary of the following text for busy professionals ({max_length} words max).",
        }

        prompt = f"{style_prompts[style]}\n\nText:\n{text}"

        return self._ai_complete({
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "temperature": 0.3,
            "max_tokens": max_length * 2,
        })

    def _ai_translate(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Translate text."""
        text = tool_input["text"]
        target_language = tool_input["target_language"]
        source_language = tool_input.get("source_language", "auto-detect")
        provider = tool_input.get("provider", self.default_provider)
        model = tool_input.get("model")

        prompt = f"Translate the following text to {target_language}. Only output the translation, nothing else.\n\nText:\n{text}"

        result = self._ai_complete({
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "temperature": 0.1,
            "max_tokens": len(text) * 2,
        })

        if result.success and result.data:
            result.data["source_language"] = source_language
            result.data["target_language"] = target_language
            result.data["translation"] = result.data.pop("content", "")

        return result

    def _ai_extract(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Extract structured data."""
        text = tool_input["text"]
        schema = tool_input.get("schema")
        fields = tool_input.get("fields", [])
        provider = tool_input.get("provider", self.default_provider)
        model = tool_input.get("model")

        if schema:
            prompt = f"""Extract data from the following text according to this JSON schema:
{json.dumps(schema, indent=2)}

Text:
{text}

Output valid JSON only."""

        elif fields:
            prompt = f"""Extract the following fields from the text: {', '.join(fields)}

Text:
{text}

Output as JSON with these exact field names."""

        else:
            prompt = f"""Extract all relevant structured data from this text as JSON:

{text}"""

        result = self._ai_complete({
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "temperature": 0.1,
            "max_tokens": 2000,
            "json_mode": provider == "openai",
        })

        if result.success and result.data:
            content = result.data.get("content", "")
            try:
                # Try to parse JSON from response
                extracted = json.loads(content)
                result.data["extracted"] = extracted
            except json.JSONDecodeError:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result.data["extracted"] = json.loads(json_match.group())
                    except:
                        result.data["extracted"] = content
                else:
                    result.data["extracted"] = content

        return result

    def _ai_compare(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Compare two texts."""
        text1 = tool_input["text1"]
        text2 = tool_input["text2"]
        method = tool_input.get("method", "embedding")

        if method == "embedding":
            # Get embeddings for both
            result1 = self._ai_embed({"text": text1})
            if not result1.success:
                return result1

            result2 = self._ai_embed({"text": text2})
            if not result2.success:
                return result2

            # Cosine similarity
            emb1 = result1.data["embeddings"]
            emb2 = result2.data["embeddings"]

            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = sum(a * a for a in emb1) ** 0.5
            norm2 = sum(b * b for b in emb2) ** 0.5
            similarity = dot_product / (norm1 * norm2) if norm1 and norm2 else 0

            return SkillResponse(
                success=True,
                message=f"Similarity: {similarity:.2%}",
                data={
                    "similarity": similarity,
                    "method": "cosine_similarity",
                    "interpretation": "identical" if similarity > 0.95 else
                                     "very similar" if similarity > 0.8 else
                                     "similar" if similarity > 0.6 else
                                     "somewhat similar" if similarity > 0.4 else
                                     "different",
                }
            )

        else:  # LLM comparison
            prompt = f"""Compare these two texts and rate their similarity from 0-100%.
Explain the key similarities and differences.

Text 1:
{text1}

Text 2:
{text2}"""

            return self._ai_complete({
                "prompt": prompt,
                "temperature": 0.3,
                "max_tokens": 500,
            })

    def _ai_models(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """List available models."""
        provider = tool_input.get("provider", "all")

        if provider == "all":
            models = {}
            for p, info in self.PROVIDERS.items():
                models[p] = {
                    "models": info.get("models", []),
                    "embedding_models": info.get("embedding_models", []),
                    "local": info.get("local", False),
                    "has_api_key": bool(self._get_api_key(p)),
                }
            return SkillResponse(
                success=True,
                message=f"Available providers: {len(self.PROVIDERS)}",
                data={"providers": models}
            )

        if provider not in self.PROVIDERS:
            return SkillResponse(
                success=False,
                message=f"Unknown provider: {provider}",
                error="unknown_provider"
            )

        info = self.PROVIDERS[provider]
        return SkillResponse(
            success=True,
            message=f"Models for {provider}",
            data={
                "provider": provider,
                "models": info.get("models", []),
                "embedding_models": info.get("embedding_models", []),
                "local": info.get("local", False),
                "has_api_key": bool(self._get_api_key(provider)),
            }
        )
