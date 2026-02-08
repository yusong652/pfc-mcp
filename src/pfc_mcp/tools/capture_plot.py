"""PFC plot capture tool with MCP image output."""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
import time
from typing import Annotated, Literal, Optional

from fastmcp import FastMCP
from mcp.types import ImageContent, TextContent
from pydantic import Field

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.config import get_bridge_config
from pfc_mcp.tools.error_messages import (
    format_bridge_unavailable,
    format_operation_error,
    is_bridge_connectivity_error,
)
from pfc_mcp.scripts import (
    DEFAULT_IMAGE_SIZE,
    DEFAULT_WALL_TRANSPARENCY,
    BallShapeType,
    CutPlane,
    VectorQuantityType,
    generate_plot_capture_script,
    normalize_ball_color_by,
    normalize_contact_color_by,
    normalize_wall_color_by,
)
from pfc_mcp.utils import PlotOutputPath


def _to_pfc_path(path: str) -> str:
    return path.replace("\\", "/")


def _create_temp_script(working_dir: str, content: str) -> Path:
    script_dir = Path(working_dir) / ".nagisa" / "plot_scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / f"capture_plot_{int(time.time() * 1000)}.py"
    script_path.write_text(content, encoding="utf-8")
    return script_path


def _cleanup_script(script_path: Path) -> None:
    try:
        script_path.unlink(missing_ok=True)
    except Exception:
        pass


async def _wait_local_file(path: Path, max_wait_s: float) -> bool:
    if path.exists():
        return True
    if max_wait_s <= 0:
        return False

    elapsed = 0.0
    step = 0.1
    while elapsed < max_wait_s:
        await asyncio.sleep(step)
        elapsed += step
        if path.exists():
            return True
    return False


def register(mcp: FastMCP) -> None:
    """Register pfc_capture_plot tool."""

    @mcp.tool()
    async def pfc_capture_plot(
        output_path: PlotOutputPath,
        size: Annotated[list[int], Field(min_length=2, max_length=2, description="Image size in pixels [width, height]")] = Field(default_factory=lambda: list(DEFAULT_IMAGE_SIZE)),
        include_ball: bool = True,
        ball_shape: BallShapeType = "sphere",
        ball_color_by: Optional[str] = Field(
            default=None,
            description=(
                "Ball coloring key (string). Examples: velocity, displacement, force-contact, "
                "radius, density, group, extra-1. Aliases like force_contact are accepted."
            ),
        ),
        ball_color_by_quantity: VectorQuantityType = "mag",
        include_wall: bool = True,
        wall_color_by: Optional[str] = Field(
            default=None,
            description=(
                "Wall coloring key (string). Examples: velocity, force-contact, name, group, extra-1."
            ),
        ),
        wall_color_by_quantity: VectorQuantityType = "mag",
        wall_transparency: Annotated[int, Field(ge=0, le=100)] = DEFAULT_WALL_TRANSPARENCY,
        include_contact: bool = False,
        contact_color_by: Optional[str] = Field(
            default="force",
            description=(
                "Contact coloring key (string). Examples: force, contact-type, model-name, "
                "fric, kn, ks, extra-1."
            ),
        ),
        contact_color_by_quantity: VectorQuantityType = "mag",
        contact_scale_by_force: bool = True,
        center: Optional[Annotated[list[float], Field(min_length=3, max_length=3, description="Camera look-at point in model coordinates [x, y, z]")]] = None,
        eye: Optional[Annotated[list[float], Field(min_length=3, max_length=3, description="Camera position in model coordinates [x, y, z]")]] = None,
        roll: Annotated[float, Field(description="Camera roll angle in degrees")] = 0.0,
        magnification: Annotated[float, Field(description="Zoom factor (1.0 = fit model, >1 = zoom in)")] = 1.0,
        projection: Literal["perspective", "parallel"] = "perspective",
        ball_cut: Optional[CutPlane] = None,
        wall_cut: Optional[CutPlane] = None,
        contact_cut: Optional[CutPlane] = None,
        timeout: Annotated[int, Field(ge=1, le=120, description="Capture timeout in seconds")] = 30,
    ) -> list[ImageContent | TextContent] | str | dict[str, str]:
        """Capture a PFC plot image and return MCP-native image content."""
        config = get_bridge_config()

        try:
            ball_color = normalize_ball_color_by(ball_color_by)
            wall_color = normalize_wall_color_by(wall_color_by)
            contact_color = normalize_contact_color_by(contact_color_by)

            view_settings: dict[str, object] = {}
            if center is not None:
                view_settings["center"] = center
            if eye is not None:
                view_settings["eye"] = eye
            if center is not None or eye is not None:
                view_settings["roll"] = roll
            if magnification != 1.0:
                view_settings["magnification"] = magnification
            if view_settings:
                view_settings["projection"] = projection

            normalized_output = _to_pfc_path(output_path)
            script_content = generate_plot_capture_script(
                output_path=normalized_output,
                plot_name="NagisaDiag",
                size=(size[0], size[1]),
                view_settings=view_settings,
                include_ball=include_ball,
                include_wall=include_wall,
                include_contact=include_contact,
                include_axes=True,
                wall_transparency=wall_transparency,
                ball_shape=ball_shape,
                ball_color_by=ball_color,
                ball_color_by_quantity=ball_color_by_quantity,
                wall_color_by=wall_color,
                wall_color_by_quantity=wall_color_by_quantity,
                contact_color_by=contact_color,
                contact_color_by_quantity=contact_color_by_quantity,
                contact_scale_by_force=contact_scale_by_force,
                ball_cut=ball_cut,
                wall_cut=wall_cut,
                contact_cut=contact_cut,
            )

            client = await get_bridge_client()
            working_dir = config.workspace_path or await client.get_working_directory()
            if not working_dir:
                return format_operation_error(
                    "pfc_capture_plot",
                    status="workspace_unavailable",
                    message="Cannot resolve pfc-bridge working directory",
                    action="Set PFC_MCP_WORKSPACE_PATH or ensure bridge has an active workspace",
                )

            script_path = _create_temp_script(working_dir, script_content)
            try:
                response = await client.execute_diagnostic(
                    script_path=_to_pfc_path(str(script_path)),
                    timeout_ms=timeout * 1000 if timeout else config.diagnostic_timeout_ms,
                )
            finally:
                _cleanup_script(script_path)

            status = response.get("status", "error")
            message = response.get("message", "")
            if status != "success":
                return format_operation_error(
                    "pfc_capture_plot",
                    status=status or "diagnostic_failed",
                    message=message or "Diagnostic execution failed",
                    action="Check bridge diagnostic logs and retry",
                )

            data = response.get("data") or {}
            result_path = Path(data.get("output_path") or output_path)
            file_ready = await _wait_local_file(result_path, config.diagnostic_file_wait_s)

            if not file_ready:
                return format_operation_error(
                    "pfc_capture_plot",
                    status="output_unavailable",
                    message="Capture completed but image is not readable locally",
                    reason=f"output_path={result_path}",
                    action="If MCP server and bridge are on different machines, transfer file or return base64 from bridge",
                )

            image_data = base64.b64encode(result_path.read_bytes()).decode("ascii")
            return [
                ImageContent(type="image", data=image_data, mimeType="image/png"),
                TextContent(type="text", text=f"Plot captured: {result_path}"),
            ]

        except ConnectionError as exc:
            return format_bridge_unavailable("pfc_capture_plot", exc)
        except TimeoutError as exc:
            return format_operation_error(
                "pfc_capture_plot",
                status="timeout",
                message="Capture timed out",
                reason=str(exc),
                action="Increase timeout or inspect bridge responsiveness",
            )
        except ValueError as exc:
            return format_operation_error(
                "pfc_capture_plot",
                status="validation_error",
                message="Parameter validation failed",
                reason=str(exc),
            )
        except Exception as exc:
            if is_bridge_connectivity_error(exc):
                return format_bridge_unavailable("pfc_capture_plot", exc)
            return format_operation_error(
                "pfc_capture_plot",
                status="internal_error",
                message="Capture failed",
                reason=str(exc),
            )
