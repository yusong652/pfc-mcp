"""Unified tool response envelope contracts.

All tool business payloads should be wrapped by this module so response
shapes stay consistent across documentation and execution tools.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field, model_validator


class ToolError(BaseModel):
    """Structured business error for tool payloads."""

    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable error summary")
    details: dict[str, Any] | None = Field(
        default=None, description="Optional structured error details"
    )


class ToolEnvelope(BaseModel):
    """Unified response shape for all tool business results."""

    ok: bool = Field(description="Business-level success flag")
    data: Any | None = Field(default=None, description="Tool-specific payload")
    error: ToolError | None = Field(default=None, description="Structured error payload")

    @model_validator(mode="after")
    def _validate_coherence(self) -> "ToolEnvelope":
        if self.ok and self.error is not None:
            raise ValueError("ok=true responses must not include error")
        if not self.ok and self.error is None:
            raise ValueError("ok=false responses must include error")
        return self


class DocsData(BaseModel):
    """Unified inner `data` schema for documentation tools."""

    source: Literal["commands", "python_api", "reference"]
    action: Literal["browse", "query"]
    entries: list[dict[str, Any]]
    summary: dict[str, Any] = Field(default_factory=dict)


def build_ok(data: Any) -> dict[str, Any]:
    """Build and validate a success envelope."""
    return ToolEnvelope(ok=True, data=data).model_dump(exclude_none=True)


def build_error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    *,
    data: Any | None = None,
) -> dict[str, Any]:
    """Build and validate an error envelope."""
    return ToolEnvelope(
        ok=False,
        data=data,
        error=ToolError(code=code, message=message, details=details),
    ).model_dump(exclude_none=True)


def build_docs_data(
    *,
    source: Literal["commands", "python_api", "reference"],
    action: Literal["browse", "query"],
    entries: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and validate documentation tool `data` payloads."""
    return DocsData(
        source=source,
        action=action,
        entries=entries,
        summary=summary or {},
    ).model_dump(exclude_none=True)


def build_error_from_legacy(
    payload: Mapping[str, Any],
    *,
    default_code: str = "operation_error",
    include_data: Any | None = None,
) -> dict[str, Any]:
    """Adapt legacy {status/message/...} payloads to unified envelope."""
    code = str(payload.get("status") or default_code)
    message = str(payload.get("message") or default_code)

    details = {
        str(k): v
        for k, v in payload.items()
        if k not in {"status", "message"}
    }
    return build_error(code, message, details or None, data=include_data)
