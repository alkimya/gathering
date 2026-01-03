-- GatheRing Database Migration
-- Migration 002: Seed LLM Providers and Models
-- Description: Inserts default providers and models with pricing

-- =============================================================================
-- PROVIDERS
-- =============================================================================

INSERT INTO agent.providers (name, display_name, api_base_url, is_local, config) VALUES
    ('anthropic', 'Anthropic', 'https://api.anthropic.com/v1', FALSE, '{"version": "2024-01-01"}'),
    ('openai', 'OpenAI', 'https://api.openai.com/v1', FALSE, '{}'),
    ('deepseek', 'DeepSeek', 'https://api.deepseek.com/v1', FALSE, '{}'),
    ('mistral', 'Mistral AI', 'https://api.mistral.ai/v1', FALSE, '{}'),
    ('google', 'Google AI', 'https://generativelanguage.googleapis.com/v1', FALSE, '{}'),
    ('ollama', 'Ollama', 'http://localhost:11434', TRUE, '{"local": true}'),
    ('groq', 'Groq', 'https://api.groq.com/openai/v1', FALSE, '{}'),
    ('together', 'Together AI', 'https://api.together.xyz/v1', FALSE, '{}')
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- MODELS - ANTHROPIC
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output, pricing_cache_read, pricing_cache_write,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active, is_default
) VALUES
-- Claude Opus 4.5 (latest flagship)
(
    (SELECT id FROM agent.providers WHERE name = 'anthropic'),
    'claude-opus-4-5', 'Claude Opus 4.5', 'claude-opus-4-5-20251101',
    15.00, 75.00, 1.50, 18.75,
    200000, 32000,
    TRUE, TRUE, TRUE, TRUE,
    TRUE, FALSE
),
-- Claude Sonnet 4 (balanced)
(
    (SELECT id FROM agent.providers WHERE name = 'anthropic'),
    'claude-sonnet-4', 'Claude Sonnet 4', 'claude-sonnet-4-20250514',
    3.00, 15.00, 0.30, 3.75,
    200000, 64000,
    TRUE, TRUE, TRUE, TRUE,
    TRUE, TRUE  -- Default model
),
-- Claude Haiku 3.5 (fast)
(
    (SELECT id FROM agent.providers WHERE name = 'anthropic'),
    'claude-haiku-3-5', 'Claude Haiku 3.5', 'claude-3-5-haiku-20241022',
    0.80, 4.00, 0.08, 1.00,
    200000, 8192,
    TRUE, TRUE, TRUE, FALSE,
    TRUE, FALSE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;

-- =============================================================================
-- MODELS - OPENAI
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active
) VALUES
-- GPT-4o (multimodal)
(
    (SELECT id FROM agent.providers WHERE name = 'openai'),
    'gpt-4o', 'GPT-4o', 'gpt-4o',
    2.50, 10.00,
    128000, 16384,
    TRUE, TRUE, TRUE, FALSE,
    TRUE
),
-- GPT-4o Mini (fast)
(
    (SELECT id FROM agent.providers WHERE name = 'openai'),
    'gpt-4o-mini', 'GPT-4o Mini', 'gpt-4o-mini',
    0.15, 0.60,
    128000, 16384,
    TRUE, TRUE, TRUE, FALSE,
    TRUE
),
-- o1 (reasoning)
(
    (SELECT id FROM agent.providers WHERE name = 'openai'),
    'o1', 'o1', 'o1',
    15.00, 60.00,
    200000, 100000,
    TRUE, TRUE, TRUE, TRUE,
    TRUE
),
-- o3-mini (reasoning fast)
(
    (SELECT id FROM agent.providers WHERE name = 'openai'),
    'o3-mini', 'o3 Mini', 'o3-mini',
    1.10, 4.40,
    200000, 100000,
    FALSE, TRUE, TRUE, TRUE,
    TRUE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;

-- =============================================================================
-- MODELS - DEEPSEEK
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active
) VALUES
-- DeepSeek V3
(
    (SELECT id FROM agent.providers WHERE name = 'deepseek'),
    'deepseek-v3', 'DeepSeek V3', 'deepseek-chat',
    0.27, 1.10,
    64000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- DeepSeek R1 (reasoning)
(
    (SELECT id FROM agent.providers WHERE name = 'deepseek'),
    'deepseek-r1', 'DeepSeek R1', 'deepseek-reasoner',
    0.55, 2.19,
    64000, 8192,
    FALSE, TRUE, TRUE, TRUE,
    TRUE
),
-- DeepSeek Coder
(
    (SELECT id FROM agent.providers WHERE name = 'deepseek'),
    'deepseek-coder', 'DeepSeek Coder', 'deepseek-coder',
    0.14, 0.28,
    128000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;

-- =============================================================================
-- MODELS - MISTRAL
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active
) VALUES
-- Mistral Large
(
    (SELECT id FROM agent.providers WHERE name = 'mistral'),
    'mistral-large', 'Mistral Large', 'mistral-large-latest',
    2.00, 6.00,
    128000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- Mistral Small
(
    (SELECT id FROM agent.providers WHERE name = 'mistral'),
    'mistral-small', 'Mistral Small', 'mistral-small-latest',
    0.20, 0.60,
    128000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- Codestral
(
    (SELECT id FROM agent.providers WHERE name = 'mistral'),
    'codestral', 'Codestral', 'codestral-latest',
    0.30, 0.90,
    256000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- Pixtral Large (multimodal)
(
    (SELECT id FROM agent.providers WHERE name = 'mistral'),
    'pixtral-large', 'Pixtral Large', 'pixtral-large-latest',
    2.00, 6.00,
    128000, 8192,
    TRUE, TRUE, TRUE, FALSE,
    TRUE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;

-- =============================================================================
-- MODELS - GOOGLE
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active
) VALUES
-- Gemini 2.0 Flash
(
    (SELECT id FROM agent.providers WHERE name = 'google'),
    'gemini-2-flash', 'Gemini 2.0 Flash', 'gemini-2.0-flash',
    0.10, 0.40,
    1000000, 8192,
    TRUE, TRUE, TRUE, TRUE,
    TRUE
),
-- Gemini 2.0 Pro
(
    (SELECT id FROM agent.providers WHERE name = 'google'),
    'gemini-2-pro', 'Gemini 2.0 Pro', 'gemini-2.0-pro',
    1.25, 5.00,
    2000000, 8192,
    TRUE, TRUE, TRUE, TRUE,
    TRUE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;

-- =============================================================================
-- MODELS - OLLAMA (Local)
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active
) VALUES
-- Llama 3.3 70B
(
    (SELECT id FROM agent.providers WHERE name = 'ollama'),
    'llama-3-3-70b', 'Llama 3.3 70B', 'llama3.3:70b',
    0, 0,
    128000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- Llama 3.2 (default local)
(
    (SELECT id FROM agent.providers WHERE name = 'ollama'),
    'llama-3-2', 'Llama 3.2', 'llama3.2',
    0, 0,
    128000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- Qwen 2.5 Coder
(
    (SELECT id FROM agent.providers WHERE name = 'ollama'),
    'qwen-2-5-coder', 'Qwen 2.5 Coder', 'qwen2.5-coder:32b',
    0, 0,
    128000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- DeepSeek R1 (local)
(
    (SELECT id FROM agent.providers WHERE name = 'ollama'),
    'deepseek-r1-local', 'DeepSeek R1 (Local)', 'deepseek-r1:32b',
    0, 0,
    64000, 8192,
    FALSE, TRUE, TRUE, TRUE,
    TRUE
),
-- Mistral (local)
(
    (SELECT id FROM agent.providers WHERE name = 'ollama'),
    'mistral-local', 'Mistral (Local)', 'mistral',
    0, 0,
    32000, 8192,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;

-- =============================================================================
-- MODELS - GROQ (Fast inference)
-- =============================================================================

INSERT INTO agent.models (
    provider_id, name, display_name, model_id,
    pricing_input, pricing_output,
    context_window, max_output,
    supports_vision, supports_tools, supports_streaming, supports_extended_thinking,
    is_active
) VALUES
-- Llama 3.3 70B on Groq
(
    (SELECT id FROM agent.providers WHERE name = 'groq'),
    'groq-llama-3-3-70b', 'Llama 3.3 70B (Groq)', 'llama-3.3-70b-versatile',
    0.59, 0.79,
    128000, 32768,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
),
-- Mixtral 8x7B on Groq
(
    (SELECT id FROM agent.providers WHERE name = 'groq'),
    'groq-mixtral', 'Mixtral 8x7B (Groq)', 'mixtral-8x7b-32768',
    0.24, 0.24,
    32768, 32768,
    FALSE, TRUE, TRUE, FALSE,
    TRUE
)
ON CONFLICT (provider_id, model_id) DO NOTHING;
