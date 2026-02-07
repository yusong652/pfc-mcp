"""Plot capture script generator used by pfc_capture_plot."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


BallShapeType = Literal["sphere", "arrow"]
VectorQuantityType = Literal["mag", "x", "y", "z"]

DEFAULT_WALL_TRANSPARENCY = 70
DEFAULT_IMAGE_SIZE = (720, 480)


class CutPlane(BaseModel):
    """Cut plane definition for clipping plot items."""

    origin: List[float] = Field(min_length=3, max_length=3)
    normal: List[float] = Field(min_length=3, max_length=3)


_EXTRA_FLEX_PATTERN = re.compile(r"^extra[\s_-]*(\d+)$", re.IGNORECASE)
_SEPARATOR_PATTERN = re.compile(r"[\s_-]+")
_VECTOR_QUANTITIES = {"mag", "x", "y", "z"}

_BALL_VECTOR = {
    "position",
    "velocity",
    "displacement",
    "spin",
    "force-contact",
    "force-applied",
    "force-unbalanced",
    "moment-contact",
    "moment-applied",
    "moment-unbalanced",
}
_BALL_SCALAR = {"radius", "damp", "density", "mass"}
_BALL_TEXT = {"id", "group"}

_WALL_VECTOR = {"position", "velocity", "displacement", "force-contact"}
_WALL_TEXT = {"name", "group"}

_CONTACT_VECTOR = {"force"}
_CONTACT_TEXT = {"id", "group", "contact-type", "model-name"}
_CONTACT_NUMERIC = {
    "fric",
    "kn",
    "ks",
    "dp_nratio",
    "dp_sratio",
    "emod",
    "kratio",
    "rr_fric",
    "rr_kr",
    "rr_slip",
}

_BALL_ALIASES = {
    "forcecontact": "force-contact",
    "forceapplied": "force-applied",
    "forceunbalanced": "force-unbalanced",
    "momentcontact": "moment-contact",
    "momentapplied": "moment-applied",
    "momentunbalanced": "moment-unbalanced",
}
_WALL_ALIASES = {"forcecontact": "force-contact"}
_CONTACT_ALIASES = {
    "contacttype": "contact-type",
    "modelname": "model-name",
    "dpnratio": "dp_nratio",
    "dpsratio": "dp_sratio",
    "rrfric": "rr_fric",
    "rrkr": "rr_kr",
    "rrslip": "rr_slip",
}


def _canonicalize(value: str, aliases: Dict[str, str]) -> str:
    raw = value.strip().lower()
    compact = _SEPARATOR_PATTERN.sub("", raw)

    if compact in aliases:
        return aliases[compact]

    extra = _EXTRA_FLEX_PATTERN.match(raw)
    if extra:
        return f"extra-{int(extra.group(1))}"

    return raw


def _validate_color_by(value: Optional[str], allowed: set[str], aliases: Dict[str, str], label: str) -> Optional[str]:
    if value is None:
        return None
    normalized = _canonicalize(value, aliases)
    if normalized in allowed or normalized.startswith("extra-"):
        return normalized
    raise ValueError(f"Invalid {label}: {value}")


def normalize_ball_color_by(value: Optional[str]) -> Optional[str]:
    return _validate_color_by(value, _BALL_VECTOR | _BALL_SCALAR | _BALL_TEXT, _BALL_ALIASES, "ball_color_by")


def normalize_wall_color_by(value: Optional[str]) -> Optional[str]:
    return _validate_color_by(value, _WALL_VECTOR | _WALL_TEXT, _WALL_ALIASES, "wall_color_by")


def normalize_contact_color_by(value: Optional[str]) -> Optional[str]:
    return _validate_color_by(
        value,
        _CONTACT_VECTOR | _CONTACT_TEXT | _CONTACT_NUMERIC,
        _CONTACT_ALIASES,
        "contact_color_by",
    )


def _normalize_quantity(quantity: str) -> str:
    q = (quantity or "mag").lower()
    return q if q in _VECTOR_QUANTITIES else "mag"


def _build_cut_command(cut: Optional[CutPlane]) -> str:
    if cut is None:
        return ""
    o = cut.origin
    n = cut.normal
    return f"cut active on type plane surface on front on back off origin ({o[0]},{o[1]},{o[2]}) normal ({n[0]},{n[1]},{n[2]})"


def _build_ball_color_by_command(color_by: Optional[str], quantity: str) -> str:
    if not color_by:
        return ""

    if color_by.startswith("extra-"):
        extra_idx = int(color_by.split("-", 1)[1])
        return (
            f'color-by numeric-attribute "extra" {extra_idx} '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by in _BALL_VECTOR:
        q = _normalize_quantity(quantity)
        return (
            f'color-by vector-attribute "{color_by}" quantity {q} '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by in _BALL_SCALAR:
        return (
            f'color-by numeric-attribute "{color_by}" '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by == "id":
        return f'color-by text-attribute "{color_by}" color-options named maximum-names 1000000 name-controls true'

    if color_by == "group":
        return "color-by text-attribute \"group\" \'Any\' color-options named maximum-names 1000000 name-controls true"

    return ""


def _build_wall_color_by_command(color_by: Optional[str], quantity: str) -> str:
    if not color_by:
        return ""

    if color_by.startswith("extra-"):
        extra_idx = int(color_by.split("-", 1)[1])
        return (
            f'color-by numeric-attribute "extra" {extra_idx} '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by in _WALL_VECTOR:
        q = _normalize_quantity(quantity)
        return (
            f'color-by vector-attribute "{color_by}" quantity {q} '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by == "name":
        return 'color-by text-attribute "name" color-options named maximum-names 1000000 name-controls true'

    if color_by == "group":
        return "color-by text-attribute \"group\" \'Any\' piece off color-options named maximum-names 1000000 name-controls true"

    return ""


def _build_contact_color_by_command(color_by: Optional[str], quantity: str) -> str:
    if not color_by:
        return ""

    if color_by.startswith("extra-"):
        extra_idx = int(color_by.split("-", 1)[1])
        return (
            f'color-by numeric-attribute "extra" {extra_idx} '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by in _CONTACT_VECTOR:
        q = _normalize_quantity(quantity)
        return (
            f'color-by vector-attribute "{color_by}" quantity {q} '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by in _CONTACT_NUMERIC:
        return (
            f'color-by numeric-property "{color_by}" '
            "color-options scaled ramp rainbow minimum automatic maximum automatic"
        )

    if color_by in {"id", "contact-type", "model-name"}:
        name = color_by.replace("-", " ")
        return f'color-by text-attribute "{name}" color-options named maximum-names 1000000 name-controls true'

    if color_by == "group":
        return "color-by text-attribute \"group\" \'Any\' color-options named maximum-names 1000000 name-controls true"

    return ""


def _build_view_command(view_settings: Optional[Dict[str, Any]]) -> str:
    if not view_settings:
        return ""

    parts: List[str] = [f"projection {view_settings.get('projection', 'perspective')}"]

    center = view_settings.get("center")
    if center:
        parts.append(f"center ({center[0]},{center[1]},{center[2]})")

    eye = view_settings.get("eye")
    if eye:
        parts.append(f"eye ({eye[0]},{eye[1]},{eye[2]})")

    if "roll" in view_settings:
        parts.append(f"roll {view_settings['roll']}")
    if "magnification" in view_settings:
        parts.append(f"magnification {view_settings['magnification']}")

    return " ".join(parts)


def generate_plot_capture_script(
    output_path: str,
    plot_name: str,
    size: Tuple[int, int],
    view_settings: Optional[Dict[str, Any]],
    include_ball: bool,
    include_wall: bool,
    include_contact: bool,
    include_axes: bool,
    wall_transparency: int,
    ball_shape: str,
    ball_color_by: Optional[str],
    ball_color_by_quantity: str,
    wall_color_by: Optional[str],
    wall_color_by_quantity: str,
    contact_color_by: Optional[str],
    contact_color_by_quantity: str,
    contact_scale_by_force: bool,
    ball_cut: Optional[CutPlane],
    wall_cut: Optional[CutPlane],
    contact_cut: Optional[CutPlane],
) -> str:
    """Generate a Python script for diagnostic plot capture in PFC."""
    lines: List[str] = [
        "import os",
        "import subprocess",
        "import itasca",
        "",
        f'output_path = r"{output_path}"',
        f'plot_name = "{plot_name}"',
        "",
        "output_dir = os.path.dirname(output_path)",
        "os.makedirs(output_dir, exist_ok=True)",
        "desktop_ini = os.path.join(output_dir, 'desktop.ini')",
        "if os.name == 'nt' and not os.path.exists(desktop_ini):",
        "    with open(desktop_ini, 'w', encoding='utf-8') as f:",
        "        f.write('[ViewState]\\nFolderType=Generic\\n')",
        "    subprocess.run(['attrib', '+H', '+S', desktop_ini], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000)",
        "",
        "itasca.command(f'plot create \"{plot_name}\"')",
        "itasca.command('plot background \"white\"')",
    ]

    view_cmd = _build_view_command(view_settings)
    if view_cmd:
        lines.append(f"itasca.command('plot view {view_cmd}')")
    else:
        lines.append("itasca.command('plot view isometric')")

    if include_ball:
        ball_cut_cmd = _build_cut_command(ball_cut)
        ball_color_cmd = _build_ball_color_by_command(ball_color_by, ball_color_by_quantity)

        use_arrow = ball_shape == "arrow" and ball_color_by in _BALL_VECTOR
        if use_arrow:
            q = _normalize_quantity(ball_color_by_quantity)
            cmd_parts = [
                "plot item create ball active on",
                "shape arrow scale automatic arrow-quality 8",
                f'color-by vector-attribute "{ball_color_by}" quantity {q}',
                "color-options scaled ramp rainbow minimum automatic maximum automatic",
                "scale-by-magnitude off",
            ]
            if ball_cut_cmd:
                cmd_parts.append(ball_cut_cmd)
            cmd_parts.append("legend active on")
            lines.append(f"itasca.command('{' '.join(cmd_parts)}')")
        else:
            cmd_parts = ["plot item create ball active on"]
            if ball_color_cmd:
                cmd_parts.append(ball_color_cmd)
            if ball_cut_cmd:
                cmd_parts.append(ball_cut_cmd)
            if ball_color_cmd or ball_cut_cmd:
                cmd_parts.append("legend active on")
            lines.append(f"itasca.command('{' '.join(cmd_parts)}')")

    if include_wall:
        wall_cut_cmd = _build_cut_command(wall_cut)
        wall_color_cmd = _build_wall_color_by_command(wall_color_by, wall_color_by_quantity)
        cmd_parts = ["plot item create wall active on"]
        if wall_color_cmd:
            cmd_parts.append(wall_color_cmd)
        cmd_parts.append(f"transparency {wall_transparency}")
        if wall_cut_cmd:
            cmd_parts.append(wall_cut_cmd)
        if wall_color_cmd or wall_cut_cmd:
            cmd_parts.append("legend active on")
        lines.append(f"itasca.command('{' '.join(cmd_parts)}')")

    if include_contact:
        contact_cut_cmd = _build_cut_command(contact_cut)
        contact_color_cmd = _build_contact_color_by_command(contact_color_by, contact_color_by_quantity)
        force_scale = "on" if contact_scale_by_force else "off"
        cmd_parts = ["plot item create contact active on"]
        if contact_color_cmd:
            cmd_parts.append(contact_color_cmd)
        cmd_parts.append(f"scale-by-force {force_scale}")
        if contact_cut_cmd:
            cmd_parts.append(contact_cut_cmd)
        if contact_color_cmd or contact_cut_cmd:
            cmd_parts.append("legend active on")
        lines.append(f"itasca.command('{' '.join(cmd_parts)}')")

    if include_axes:
        lines.append("itasca.command('plot item create axes')")

    lines.extend(
        [
            "",
            f"itasca.command(f'plot \"{{plot_name}}\" export bitmap filename \"{{output_path}}\" size {size[0]} {size[1]}')",
            "result = {'output_path': output_path}",
            "print(f'Plot export initiated: {output_path}')",
        ]
    )
    return "\n".join(lines)
