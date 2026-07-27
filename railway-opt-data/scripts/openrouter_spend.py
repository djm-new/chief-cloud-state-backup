#!/usr/bin/env python3
"""OpenRouter spend tracking helpers for Hermes-owned scripts.

Use this module as the single code path for OpenRouter HTTP calls so token
usage, cost estimation, and spend ledger writes happen automatically for any
new project that uses the shared helper.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import requests
from types import SimpleNamespace

try:
    from agent.spend_ledger import SpendEvent, record_spend_event
except Exception:  # pragma: no cover - optional accounting dependency
    @dataclass(frozen=True)
    class SpendEvent:  # type: ignore[no-redef]
        provider: str = ""
        model: str = ""
        api_mode: str = ""
        base_url: str = ""
        session_id: str = ""
        parent_session_id: str = ""
        source: str = ""
        platform: str = ""
        chat_id: str = ""
        chat_name: str = ""
        chat_type: str = ""
        thread_id: str = ""
        channel_label: str = ""
        gateway_session_key: str = ""
        workdir: str = ""
        project_slug: str = ""
        input_tokens: int = 0
        output_tokens: int = 0
        cache_read_tokens: int = 0
        cache_write_tokens: int = 0
        reasoning_tokens: int = 0
        prompt_tokens: int = 0
        total_tokens: int = 0
        request_count: int = 0
        estimated_cost_usd: float | None = None
        cost_status: str = "unknown"
        cost_source: str = "unknown"
        pricing_version: str = ""
        latency_ms: int | None = None
        success: bool = True
        provider_request_id: str = ""
        raw_usage: Any = None
        metadata: dict[str, Any] | None = None
        created_at: float | None = None

    def record_spend_event(*_args, **_kwargs):
        return None

try:
    from agent.usage_pricing import estimate_usage_cost, normalize_usage
except Exception:  # pragma: no cover - optional accounting dependency
    def normalize_usage(usage: dict[str, Any] | None, provider: str = "openrouter", api_mode: str = DEFAULT_API_MODE):
        usage = usage or {}
        return SimpleNamespace(
            input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
            cache_read_tokens=int(usage.get("cache_read_tokens") or 0),
            cache_write_tokens=int(usage.get("cache_write_tokens") or 0),
            reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
            request_count=1,
            raw_usage=usage,
        )

    def estimate_usage_cost(*_args, **_kwargs):
        return SimpleNamespace(amount_usd=None, status="unknown", source="unavailable", pricing_version="")

DEFAULT_PROJECT_SLUG = "podcast-intelligence-digest"
DEFAULT_SOURCE = "cron"
DEFAULT_PLATFORM = "cron"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_API_MODE = "chat_completions"
DEFAULT_REFERER = "https://hermes-agent.local"


@dataclass(frozen=True)
class OpenRouterSpendResult:
    estimated_cost_usd: Optional[float]
    cost_status: str
    cost_source: str
    pricing_version: str
    canonical_usage: Any


def gateway_env_key(name: str = "OPENROUTER_API_KEY") -> str | None:
    """Resolve current gateway env, falling back to PID 1 for stale subprocess envs."""
    val = os.getenv(name)
    if val:
        return val
    try:
        for item in Path('/proc/1/environ').read_bytes().split(b'\0'):
            if item.startswith((name + '=').encode()):
                return item.split(b'=', 1)[1].decode()
    except Exception:
        pass
    return None


def build_openrouter_headers(*, api_key: str | None = None, title: str = "Hermes OpenRouter Request", referer: str = DEFAULT_REFERER) -> dict[str, str]:
    key = api_key or gateway_env_key()
    if not key:
        raise RuntimeError('OPENROUTER_API_KEY not found in env or /proc/1/environ')
    return {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': referer,
        'X-Title': title,
    }


def _usage_as_object(usage: dict[str, Any] | None) -> Any:
    """Convert raw dict payloads into an attribute-access object when needed."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        return SimpleNamespace(**usage)
    return usage


def record_openrouter_usage(
    *,
    model: str,
    usage: dict[str, Any] | None,
    provider_request_id: str = "",
    api_mode: str = DEFAULT_API_MODE,
    base_url: str = DEFAULT_BASE_URL,
    source: str = DEFAULT_SOURCE,
    platform: str = DEFAULT_PLATFORM,
    project_slug: str = DEFAULT_PROJECT_SLUG,
    workdir: str = "/opt/data/podcast_digest",
    session_id: str = "",
    parent_session_id: str = "",
    chat_id: str = "",
    chat_name: str = "",
    chat_type: str = "",
    thread_id: str = "",
    channel_label: str = "",
    gateway_session_key: str = "",
    latency_ms: int | None = None,
    metadata: Optional[dict[str, Any]] = None,
    created_at: float | None = None,
) -> OpenRouterSpendResult:
    """Normalize OpenRouter usage and persist a spend event.

    Best-effort only: callers should let exceptions bubble only if they want
    the pipeline to fail. The intent is to keep the ledger in sync with direct
    OpenRouter HTTP calls made by Hermes-owned scripts.
    """
    canonical = normalize_usage(_usage_as_object(usage), provider="openrouter", api_mode=api_mode)
    cost_result = estimate_usage_cost(
        model,
        canonical,
        provider="openrouter",
        base_url=base_url,
        api_key="",
    )
    try:
        record_spend_event(
            SpendEvent(
                provider="openrouter",
                model=model or "unknown",
                api_mode=api_mode,
                base_url=base_url,
                session_id=session_id,
                parent_session_id=parent_session_id,
                source=source,
                platform=platform,
                chat_id=chat_id,
                chat_name=chat_name,
                chat_type=chat_type,
                thread_id=thread_id,
                channel_label=channel_label,
                gateway_session_key=gateway_session_key,
                workdir=workdir,
                project_slug=project_slug,
                input_tokens=canonical.input_tokens,
                output_tokens=canonical.output_tokens,
                cache_read_tokens=canonical.cache_read_tokens,
                cache_write_tokens=canonical.cache_write_tokens,
                reasoning_tokens=canonical.reasoning_tokens,
                prompt_tokens=canonical.prompt_tokens,
                total_tokens=canonical.total_tokens,
                request_count=canonical.request_count,
                estimated_cost_usd=float(cost_result.amount_usd) if cost_result.amount_usd is not None else None,
                cost_status=cost_result.status,
                cost_source=cost_result.source,
                pricing_version=cost_result.pricing_version or "",
                latency_ms=latency_ms,
                success=True,
                provider_request_id=provider_request_id,
                raw_usage=canonical.raw_usage if isinstance(canonical.raw_usage, dict) else usage,
                metadata=metadata or {},
                created_at=created_at,
            )
        )
    except Exception:
        # Never let accounting break the underlying script.
        pass
    return OpenRouterSpendResult(
        estimated_cost_usd=float(cost_result.amount_usd) if cost_result.amount_usd is not None else None,
        cost_status=cost_result.status,
        cost_source=cost_result.source,
        pricing_version=cost_result.pricing_version or "",
        canonical_usage=canonical,
    )


def openrouter_post_json(
    *,
    path: str,
    payload: dict[str, Any],
    model: str,
    title: str = "Hermes OpenRouter Request",
    referer: str = DEFAULT_REFERER,
    api_key: str | None = None,
    timeout: int = 180,
    base_url: str = DEFAULT_BASE_URL,
    api_mode: str = DEFAULT_API_MODE,
    source: str = DEFAULT_SOURCE,
    platform: str = DEFAULT_PLATFORM,
    project_slug: str | None = None,
    workdir: str | None = None,
    session_id: str = "",
    parent_session_id: str = "",
    chat_id: str = "",
    chat_name: str = "",
    chat_type: str = "",
    thread_id: str = "",
    channel_label: str = "",
    gateway_session_key: str = "",
    latency_ms: int | None = None,
    metadata: Optional[dict[str, Any]] = None,
    created_at: float | None = None,
) -> dict[str, Any]:
    """POST JSON to OpenRouter and record spend from the response usage block.

    This is the shared code path to use in new Hermes projects. It keeps the
    OpenRouter token tracker and spend ledger in sync automatically.
    """
    headers = build_openrouter_headers(api_key=api_key, title=title, referer=referer)
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:2000]}")
    data = resp.json()
    record_openrouter_usage(
        model=model,
        usage=data.get('usage', {}),
        provider_request_id=str(data.get('id', '') or ''),
        api_mode=api_mode,
        base_url=base_url,
        source=source,
        platform=platform,
        project_slug=project_slug or os.getenv('HERMES_PROJECT_SLUG') or Path.cwd().name or DEFAULT_PROJECT_SLUG,
        workdir=workdir or str(Path.cwd()),
        session_id=session_id,
        parent_session_id=parent_session_id,
        chat_id=chat_id,
        chat_name=chat_name,
        chat_type=chat_type,
        thread_id=thread_id,
        channel_label=channel_label,
        gateway_session_key=gateway_session_key,
        latency_ms=latency_ms,
        metadata=metadata,
        created_at=created_at,
    )
    return data
