"""PFC Python API Browse Tool - Navigate and retrieve Python SDK documentation."""

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.contracts import build_docs_data, build_error, build_ok
from pfc_mcp.docs.python_api import APILoader


def register(mcp: FastMCP):
    """Register pfc_browse_python_api tool with the MCP server."""

    @mcp.tool()
    def pfc_browse_python_api(
        api: Optional[str] = Field(
            None,
            description=(
                "PFC Python API path to browse (dot-separated, starting from itasca). Examples:\n"
                "- None or '': Root overview - all modules and objects\n"
                "- 'itasca': Core module functions (command, cycle, gravity, etc.)\n"
                "- 'itasca.ball': Ball module functions (create, find, list, etc.)\n"
                "- 'itasca.ball.create': Specific function documentation\n"
                "- 'itasca.ball.Ball': Ball object method groups\n"
                "- 'itasca.ball.Ball.pos': Specific method documentation\n"
                "- 'itasca.wall.facet': Nested submodule\n"
                "- 'itasca.wall.facet.Facet': Facet object in wall.facet module"
            )
        )
    ) -> Dict[str, Any]:
        """Browse PFC Python SDK documentation by path (like glob + cat)."""
        normalized = _normalize_api_path(api)

        if not normalized:
            return build_ok(_browse_root())

        if normalized == "itasca":
            return _wrap_payload(_browse_module("itasca"))

        parsed = _parse_api_path(normalized)

        if parsed["type"] == "error":
            return _wrap_payload(_browse_with_fallback(parsed, normalized))

        if parsed["type"] == "module":
            payload = _browse_module(parsed["module_path"])
            return _wrap_payload(payload)
        if parsed["type"] == "function":
            payload = _browse_function(parsed["module_path"], parsed["name"])
            return _wrap_payload(payload)
        if parsed["type"] == "object":
            payload = _browse_object(
                parsed["module_path"],
                parsed["name"],
                parsed.get("display_name"),
            )
            return _wrap_payload(payload)
        if parsed["type"] == "method":
            payload = _browse_method(
                parsed["module_path"],
                parsed["object_name"],
                parsed["name"],
                parsed.get("display_name"),
            )
            return _wrap_payload(payload)

        return build_error(
            code="unknown_parse_type",
            message=f"Unknown parse result type: {parsed['type']}",
            details={"path": normalized},
        )


def _normalize_api_path(api: Optional[str]) -> str:
    if api is None:
        return ""
    return api.strip()


def _parse_api_path(api: str) -> Dict[str, Any]:
    if not api.startswith("itasca"):
        return {
            "type": "error",
            "error": f"Path must start with 'itasca', got: {api}",
            "fallback_path": "",
        }

    parts = api.split(".")
    index = APILoader.load_index()
    modules = index.get("modules", {})
    objects = index.get("objects", {})

    object_index = None
    for i, part in enumerate(parts):
        if i > 0 and part[0].isupper():
            object_index = i
            break

    if object_index is not None:
        module_parts = parts[:object_index]
        module_path = ".".join(module_parts)
        object_name = parts[object_index]

        actual_object_name = object_name
        if object_name not in objects:
            contact_data = objects.get("Contact", {})
            contact_types = contact_data.get("types", [])
            if object_name in contact_types:
                actual_object_name = "Contact"
            else:
                return {
                    "type": "error",
                    "error": f"Object '{object_name}' not found",
                    "fallback_path": module_path,
                }

        if len(parts) == object_index + 1:
            return {
                "type": "object",
                "module_path": module_path,
                "name": actual_object_name,
                "display_name": object_name,
            }

        method_name = parts[object_index + 1]
        return {
            "type": "method",
            "module_path": module_path,
            "object_name": actual_object_name,
            "display_name": object_name,
            "name": method_name,
        }

    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        index_key = _path_to_index_key(candidate)

        if index_key in modules:
            if length == len(parts):
                return {
                    "type": "module",
                    "module_path": candidate,
                }

            func_name = parts[length]
            return {
                "type": "function",
                "module_path": candidate,
                "name": func_name,
            }

    return {
        "type": "error",
        "error": f"Module path not found: {api}",
        "fallback_path": ".".join(parts[:-1]) if len(parts) > 1 else "",
    }


def _path_to_index_key(full_path: str) -> str:
    if full_path == "itasca":
        return "itasca"
    if full_path.startswith("itasca."):
        return full_path[7:]
    return full_path


def _format_module_path(index_key: str) -> str:
    if index_key == "itasca":
        return "itasca"
    return f"itasca.{index_key}"


def _extract_function_names(functions: List[Any]) -> List[str]:
    names: List[str] = []
    for func in functions:
        if isinstance(func, dict):
            name = func.get("name")
            if name:
                names.append(name)
        elif isinstance(func, str):
            names.append(func)
    return names


def _browse_root() -> Dict[str, Any]:
    index = APILoader.load_index()
    modules = index.get("modules", {})
    objects = index.get("objects", {})

    module_items: List[Dict[str, Any]] = []
    for module_key, module_info in modules.items():
        module_items.append(
            {
                "entry_type": "module",
                "path": _format_module_path(module_key),
                "description": module_info.get("description", ""),
                "function_count": len(module_info.get("functions", [])),
            }
        )

    object_items: List[Dict[str, Any]] = []
    for object_name, object_info in objects.items():
        object_items.append(
            {
                "entry_type": "object",
                "name": object_name,
                "description": object_info.get("description", ""),
                "file": object_info.get("file"),
                "types": object_info.get("types"),
            }
        )

    entries = module_items + object_items
    return build_docs_data(
        source="python_api",
        action="browse",
        entries=entries,
        summary={
            "count": len(entries),
            "total_modules": len(module_items),
            "total_objects": len(object_items),
        },
    )


def _browse_module(module_path: str) -> Dict[str, Any]:
    index_key = _path_to_index_key(module_path)
    module_data = APILoader.load_module(index_key)

    if not module_data:
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "module_not_found",
                "message": f"Module not found: {module_path}",
            },
            "input": {"module_path": module_path},
        }

    index = APILoader.load_index()
    objects = index.get("objects", {})
    related_objects = []
    for obj_name, obj_data in objects.items():
        file_path = obj_data.get("file", "")
        if index_key in file_path or (index_key == "itasca" and "/" not in file_path):
            related_objects.append(obj_name)

    functions = module_data.get("functions", [])
    function_names = _extract_function_names(functions)

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[{"entry_type": "function", "name": name} for name in function_names],
        summary={
            "count": len(function_names),
            "module_path": module_path,
            "module": module_data,
            "related_objects": sorted(related_objects),
        },
    )


def _browse_function(module_path: str, func_name: str) -> Dict[str, Any]:
    index_key = _path_to_index_key(module_path)
    func_doc = APILoader.load_function(index_key, func_name)

    if not func_doc:
        module_data = APILoader.load_module(index_key) or {}
        available_functions = _extract_function_names(module_data.get("functions", []))
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "function_not_found",
                "message": f"Function '{func_name}' not found in {module_path}",
            },
            "input": {"module_path": module_path, "function": func_name},
            "available_functions": available_functions,
        }

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[
            {
                "module_path": module_path,
                "function": func_name,
                "doc": func_doc,
            }
        ],
        summary={"count": 1},
    )


def _browse_object(module_path: str, object_name: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    object_doc = APILoader.load_object(object_name)
    shown_name = display_name or object_name

    if not object_doc:
        index = APILoader.load_index()
        available_objects = sorted(index.get("objects", {}).keys())
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "object_not_found",
                "message": f"Object not found: {shown_name}",
            },
            "input": {"module_path": module_path, "object": shown_name},
            "available_objects": available_objects,
        }

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[
            {
                "module_path": module_path,
                "object": shown_name,
                "actual_object": object_name,
                "doc": object_doc,
            }
        ],
        summary={"count": 1},
    )


def _browse_method(
    module_path: str,
    object_name: str,
    method_name: str,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    method_doc = APILoader.load_method(object_name, method_name)
    shown_name = display_name or object_name

    if not method_doc:
        object_doc = APILoader.load_object(object_name) or {}
        method_names = _extract_function_names(object_doc.get("methods", []))
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "method_not_found",
                "message": f"Method '{method_name}' not found in {shown_name}",
            },
            "input": {
                "module_path": module_path,
                "object": shown_name,
                "actual_object": object_name,
                "method": method_name,
            },
            "available_methods": method_names,
        }

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[
            {
                "module_path": module_path,
                "object": shown_name,
                "actual_object": object_name,
                "method": method_name,
                "doc": method_doc,
            }
        ],
        summary={"count": 1},
    )


def _browse_with_fallback(parsed: Dict[str, Any], requested_api: str) -> Dict[str, Any]:
    error_msg = parsed.get("error", "Unknown error")
    fallback_path = parsed.get("fallback_path", "")

    index = APILoader.load_index()
    modules = index.get("modules", {})
    available_modules = sorted(_format_module_path(module_key) for module_key in modules.keys())

    return {
        "source": "python_api",
        "action": "browse",
        "error": {
            "code": "invalid_path",
            "message": error_msg,
        },
        "input": {"api": requested_api},
        "fallback_path": fallback_path or "itasca",
        "available_modules": available_modules,
    }


def _wrap_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in payload:
        err = payload.get("error") or {}
        details = {k: v for k, v in payload.items() if k != "error"}
        return build_error(
            code=str(err.get("code") or "browse_error"),
            message=str(err.get("message") or "Browse failed"),
            details=details or None,
        )
    return build_ok(payload)
