"""PFC Python API Browse Tool - Navigate and retrieve Python SDK documentation."""

from typing import Optional, Dict, Any

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.docs.python_api import APILoader, APIFormatter


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
    ) -> str:
        """Browse PFC Python SDK documentation by path (like glob + cat).

        Paths use Python dot notation starting from 'itasca'.

        Navigation levels:
        - Root (no api): All modules and objects overview
        - Module (itasca.ball): Module functions list
        - Function (itasca.ball.create): Full function documentation
        - Object (itasca.ball.Ball): Object method groups
        - Method (itasca.ball.Ball.pos): Full method documentation

        When to use:
        - You know the API path (module.function or module.Object.method)
        - You want to explore available functions/methods

        Related tools:
        - pfc_query_python_api: Search API by keywords (when path unknown)
        - pfc_browse_commands: PFC command syntax documentation
        """
        normalized = _normalize_api_path(api)

        if not normalized:
            return _browse_root()

        if normalized == "itasca":
            return _browse_module("itasca")

        parsed = _parse_api_path(normalized)

        if parsed["type"] == "error":
            return _browse_with_fallback(parsed)

        if parsed["type"] == "module":
            return _browse_module(parsed["module_path"])
        elif parsed["type"] == "function":
            return _browse_function(parsed["module_path"], parsed["name"])
        elif parsed["type"] == "object":
            return _browse_object(
                parsed["module_path"],
                parsed["name"],
                parsed.get("display_name")
            )
        elif parsed["type"] == "method":
            return _browse_method(
                parsed["module_path"],
                parsed["object_name"],
                parsed["name"],
                parsed.get("display_name")
            )
        else:
            return f"Unknown parse result type: {parsed['type']}"


def _normalize_api_path(api: Optional[str]) -> str:
    if api is None:
        return ""
    return api.strip()


def _parse_api_path(api: str) -> Dict[str, Any]:
    if not api.startswith("itasca"):
        return {
            "type": "error",
            "error": f"Path must start with 'itasca', got: {api}",
            "fallback_path": ""
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
                    "fallback_path": module_path
                }

        if len(parts) == object_index + 1:
            return {
                "type": "object",
                "module_path": module_path,
                "name": actual_object_name,
                "display_name": object_name
            }
        else:
            method_name = parts[object_index + 1]
            return {
                "type": "method",
                "module_path": module_path,
                "object_name": actual_object_name,
                "display_name": object_name,
                "name": method_name
            }
    else:
        for length in range(len(parts), 0, -1):
            candidate = ".".join(parts[:length])
            index_key = _path_to_index_key(candidate)

            if index_key in modules:
                if length == len(parts):
                    return {
                        "type": "module",
                        "module_path": candidate
                    }
                else:
                    func_name = parts[length]
                    return {
                        "type": "function",
                        "module_path": candidate,
                        "name": func_name
                    }

        return {
            "type": "error",
            "error": f"Module path not found: {api}",
            "fallback_path": ".".join(parts[:-1]) if len(parts) > 1 else ""
        }


def _path_to_index_key(full_path: str) -> str:
    if full_path == "itasca":
        return "itasca"
    if full_path.startswith("itasca."):
        return full_path[7:]
    return full_path


def _browse_root() -> str:
    index = APILoader.load_index()
    modules = index.get("modules", {})
    objects = index.get("objects", {})
    return APIFormatter.format_root(modules, objects)


def _browse_module(module_path: str) -> str:
    index_key = _path_to_index_key(module_path)
    module_data = APILoader.load_module(index_key)

    if not module_data:
        return f"Module not found: {module_path}"

    index = APILoader.load_index()
    objects = index.get("objects", {})
    related_objects = []
    for obj_name, obj_data in objects.items():
        file_path = obj_data.get("file", "")
        if index_key in file_path or (index_key == "itasca" and "/" not in file_path):
            related_objects.append(obj_name)

    return APIFormatter.format_module(module_path, module_data, related_objects)


def _browse_function(module_path: str, func_name: str) -> str:
    index_key = _path_to_index_key(module_path)
    func_doc = APILoader.load_function(index_key, func_name)

    if not func_doc:
        error_msg = f"Function '{func_name}' not found in {module_path}"
        module_data = APILoader.load_module(index_key)
        if module_data:
            module_content = APIFormatter.format_module(module_path, module_data)
            return APIFormatter.format_with_error(error_msg, module_content)
        return error_msg

    content = APIFormatter.format_function(func_doc, module_path)

    navigation = f"""

Navigation:
- pfc_browse_python_api(api="{module_path}") for module overview
- pfc_browse_python_api() for root
"""
    return content + navigation


def _browse_object(module_path: str, object_name: str, display_name: Optional[str] = None) -> str:
    object_doc = APILoader.load_object(object_name)

    if not object_doc:
        return f"Object not found: {object_name}"

    return APIFormatter.format_object(module_path, object_name, object_doc, display_name)


def _browse_method(module_path: str, object_name: str, method_name: str, display_name: Optional[str] = None) -> str:
    method_doc = APILoader.load_method(object_name, method_name)

    shown_name = display_name or object_name

    if not method_doc:
        error_msg = f"Method '{method_name}' not found in {shown_name}"
        object_doc = APILoader.load_object(object_name)
        if object_doc:
            object_content = APIFormatter.format_object(module_path, object_name, object_doc, display_name)
            return APIFormatter.format_with_error(error_msg, object_content)
        return error_msg

    content = APIFormatter.format_method(method_doc, shown_name, actual_object_name=object_name)

    full_path = f"{module_path}.{shown_name}"
    navigation = f"""

Navigation:
- pfc_browse_python_api(api="{full_path}") for object overview
- pfc_browse_python_api(api="{module_path}") for module overview
"""
    return content + navigation


def _browse_with_fallback(parsed: Dict[str, Any]) -> str:
    error_msg = parsed.get("error", "Unknown error")
    fallback_path = parsed.get("fallback_path", "")

    if not fallback_path:
        index = APILoader.load_index()
        modules = index.get("modules", {})
        objects = index.get("objects", {})
        fallback_content = APIFormatter.format_root(modules, objects)
    else:
        normalized = _normalize_api_path(fallback_path)
        if not normalized or normalized == "itasca":
            index = APILoader.load_index()
            modules = index.get("modules", {})
            objects = index.get("objects", {})
            fallback_content = APIFormatter.format_root(modules, objects)
        else:
            re_parsed = _parse_api_path(normalized)
            if re_parsed["type"] == "module":
                index_key = _path_to_index_key(re_parsed["module_path"])
                module_data = APILoader.load_module(index_key)
                if module_data:
                    fallback_content = APIFormatter.format_module(re_parsed["module_path"], module_data)
                else:
                    index = APILoader.load_index()
                    modules = index.get("modules", {})
                    objects = index.get("objects", {})
                    fallback_content = APIFormatter.format_root(modules, objects)
            elif re_parsed["type"] == "object":
                object_doc = APILoader.load_object(re_parsed["name"])
                if object_doc:
                    fallback_content = APIFormatter.format_object(
                        re_parsed["module_path"], re_parsed["name"], object_doc
                    )
                else:
                    index = APILoader.load_index()
                    modules = index.get("modules", {})
                    objects = index.get("objects", {})
                    fallback_content = APIFormatter.format_root(modules, objects)
            else:
                index = APILoader.load_index()
                modules = index.get("modules", {})
                objects = index.get("objects", {})
                fallback_content = APIFormatter.format_root(modules, objects)

    return APIFormatter.format_with_error(error_msg, fallback_content)
