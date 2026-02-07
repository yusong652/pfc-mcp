"""Data loading layer for PFC SDK documentation.

This module is responsible for loading documentation data from JSON files
and providing cached access to avoid repeated I/O operations.

Responsibilities:
- Load index.json (quick reference and metadata)
- Load keywords.json files (from all modules)
- Load individual API documentation files
- Cache loaded data for performance
"""

from typing import Dict, Any, Optional, List
from functools import lru_cache
from collections import defaultdict
from pathlib import Path
import json

from pfc_mcp.docs.config import PFC_DOCS_SOURCE


class DocumentationLoader:
    """Loads and caches SDK documentation data.

    This class provides static methods for loading various documentation
    resources. All methods use caching to avoid repeated file I/O.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def load_index() -> Dict[str, Any]:
        """Load the main index file with caching.

        The index file contains:
        - quick_ref: Direct API name to file reference mapping
        - keywords: Keyword to API list mapping (if present)
        - fallback_hints: Suggestions when SDK doesn't support operation

        Post-processing:
        - Expands Contact.* entries to all Contact type variants
          (BallBallContact, BallFacetContact, etc.)

        Returns:
            Dict containing index data structure

        Raises:
            FileNotFoundError: If index.json doesn't exist

        Example:
            >>> index = DocumentationLoader.load_index()
            >>> quick_ref = index["quick_ref"]
            >>> "itasca.ball.create" in quick_ref
            True
            >>> "BallBallContact.gap" in quick_ref  # Expanded from Contact.gap
            True
        """
        index_path = PFC_DOCS_SOURCE / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        # Expand Contact.* entries to all Contact type variants
        index = DocumentationLoader._expand_contact_types(index)

        # Expand object methods to full official paths
        index = DocumentationLoader._expand_object_methods(index)

        return index

    @staticmethod
    @lru_cache(maxsize=1)
    def load_all_keywords() -> Dict[str, List[str]]:
        """Load keywords from all modules with caching and merging.

        Aggregates keywords from:
        - itasca_keywords.json (top-level module)
        - modules/**/keywords.json (all modules and submodules recursively)

        Uses merge strategy: when multiple modules define the same keyword,
        all associated APIs are collected (not overwritten).

        Post-processing:
        - Expands itasca.contact.Contact.* entries to all Contact type variants
          (same expansion as index loading for consistency)

        Returns:
            Dict mapping keywords to list of API names

        Example:
            >>> keywords = DocumentationLoader.load_all_keywords()
            >>> keywords["create ball"]
            ["itasca.ball.create"]
            >>> keywords["normal vector"]  # Merged from multiple modules
            ["Facet.normal", "Contact.normal"]
            >>> keywords["contact gap"]  # Expanded to all Contact types
            ["itasca.BallBallContact.gap", "itasca.BallFacetContact.gap", ...]
        """
        # Use defaultdict to automatically handle merging
        all_keywords = defaultdict(list)

        # Load itasca top-level keywords
        itasca_keywords_path = PFC_DOCS_SOURCE / "itasca_keywords.json"
        if itasca_keywords_path.exists():
            with open(itasca_keywords_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                DocumentationLoader._merge_keywords(all_keywords, data.get("keywords", {}))

        # Load keywords from all sub-modules (recursive)
        modules_dir = PFC_DOCS_SOURCE / "modules"
        if modules_dir.exists():
            DocumentationLoader._load_keywords_recursive(modules_dir, all_keywords)

        # Expand Contact.* entries to all Contact type variants
        all_keywords = DocumentationLoader._expand_contact_keywords(all_keywords)

        # Convert defaultdict back to regular dict for return
        return dict(all_keywords)

    @staticmethod
    def load_api_doc(api_name: str) -> Optional[Dict[str, Any]]:
        """Load documentation for a specific API or module.

        Args:
            api_name: Full API name like "itasca.ball.create" or "Ball.vel"
                     or module name like "itasca.ball"

        Returns:
            API documentation dict with fields:

            For functions/methods:
                - signature: Function signature
                - description: Detailed description
                - parameters: List of parameter definitions
                - returns: Return value information
                - examples: Usage examples
                - limitations: Known limitations (optional)
                - fallback_commands: Alternative commands (optional)
                - best_practices: Recommended practices (optional)
                - notes: Additional notes (optional)
                - see_also: Related APIs (optional)

            For modules:
                - type: "module"
                - signature: Module signature with function count
                - description: Module description
                - available_functions: List of all function names in the module
                - usage_note: Guidance on querying specific functions

            Returns None if API not found.

        Example:
            >>> doc = DocumentationLoader.load_api_doc("itasca.ball.create")
            >>> doc["signature"]
            "itasca.ball.create(radius, pos=None)"

            >>> doc = DocumentationLoader.load_api_doc("itasca.ball")
            >>> doc["type"]
            "module"
            >>> len(doc["available_functions"])
            9
        """
        index = DocumentationLoader.load_index()

        # Try 1: Get file reference from quick_ref (functions/methods)
        ref = index["quick_ref"].get(api_name)
        if not ref:
            # Try 2: Check if it's a module name
            module_doc = DocumentationLoader._load_module_doc(api_name, index)
            if module_doc:
                return module_doc
            # Not found in either quick_ref or modules
            return None

        # Parse file path and anchor
        # Format: "file_name.json#function_name"
        file_name, anchor = ref.split('#')
        doc_path = PFC_DOCS_SOURCE / file_name

        if not doc_path.exists():
            return None

        with open(doc_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)

        # Find the specific function or method
        # Object method files contain "methods" key
        # Module function files contain "functions" key
        if "methods" in doc:
            for method in doc["methods"]:
                if method["name"] == anchor:
                    return method
        elif "functions" in doc:
            for func in doc["functions"]:
                if func["name"] == anchor:
                    return func

        return None

    @staticmethod
    def _expand_contact_types(index: Dict[str, Any]) -> Dict[str, Any]:
        """Expand Contact.* entries to all Contact type variants.

        PFC has multiple Contact types (BallBallContact, BallFacetContact, etc.)
        that share the same interface documented as "Contact". This method
        expands each Contact.* entry to all Contact type variants so that
        LLM can search using official API paths.

        Args:
            index: Loaded index dictionary

        Returns:
            Modified index with expanded Contact entries

        Example:
            Input quick_ref:
                "Contact.gap": "modules/contact/Contact.json#gap"

            Output quick_ref:
                "BallBallContact.gap": "modules/contact/Contact.json#gap"
                "BallFacetContact.gap": "modules/contact/Contact.json#gap"
                "BallPebbleContact.gap": "modules/contact/Contact.json#gap"
                "PebblePebbleContact.gap": "modules/contact/Contact.json#gap"
                "PebbleFacetContact.gap": "modules/contact/Contact.json#gap"
        """
        from pfc_mcp.docs.python_api.types.contact import CONTACT_TYPES

        quick_ref = index.get("quick_ref", {})

        # Find all Contact.* entries
        contact_entries = {}
        entries_to_remove = []

        for api_name, file_ref in quick_ref.items():
            # Format 1: Short format "Contact.gap" (legacy)
            if api_name.startswith("Contact."):
                # Extract method name
                method_name = api_name.split(".", 1)[1]
                contact_entries[method_name] = file_ref
                entries_to_remove.append(api_name)
            # Format 2: Unified format "itasca.contact.Contact.gap" (preferred)
            elif api_name.startswith("itasca.contact.Contact."):
                # Extract method name after "itasca.contact.Contact."
                method_name = api_name.split(".", 3)[3]
                contact_entries[method_name] = file_ref
                entries_to_remove.append(api_name)

        # Expand each Contact.* entry to all Contact types
        for method_name, file_ref in contact_entries.items():
            for contact_type in CONTACT_TYPES:
                # Create only full official paths: itasca.BallBallContact.gap
                # This eliminates the need for PathResolver to add "itasca." prefix
                full_path = f"itasca.{contact_type}.{method_name}"
                quick_ref[full_path] = file_ref

        # Remove original Contact.* entries (they're now replaced by specific types)
        for api_name in entries_to_remove:
            del quick_ref[api_name]

        return index

    @staticmethod
    def _expand_object_methods(index: Dict[str, Any]) -> Dict[str, Any]:
        """Expand object method entries to full official paths.

        Object methods like "Ball.vel", "Wall.pos" are stored in index as short paths.
        This method expands them to full official paths like "itasca.ball.Ball.vel",
        "itasca.wall.Wall.pos", eliminating the need for runtime path resolution.

        Args:
            index: Loaded index dictionary

        Returns:
            Modified index with expanded object method entries

        Example:
            Input quick_ref:
                "Ball.vel": "modules/ball/Ball.json#vel"
                "Wall.pos": "modules/wall/Wall.json#pos"

            Output quick_ref:
                "itasca.ball.Ball.vel": "modules/ball/Ball.json#vel"
                "itasca.wall.Wall.pos": "modules/wall/Wall.json#pos"
        """
        from pfc_mcp.docs.python_api.types.mappings import CLASS_TO_MODULE

        quick_ref = index.get("quick_ref", {})

        # Find all object method entries (Class.method format, not starting with itasca.)
        object_methods = {}
        entries_to_remove = []

        for api_name, file_ref in quick_ref.items():
            # Skip if already full path or module function
            if api_name.startswith("itasca."):
                continue

            # Check if it's an object method (Class.method format)
            if '.' in api_name:
                class_name = api_name.split('.')[0]
                # Check if it's a known class with module mapping
                if class_name in CLASS_TO_MODULE:
                    object_methods[api_name] = file_ref
                    entries_to_remove.append(api_name)

        # Expand each object method to full path
        for short_path, file_ref in object_methods.items():
            class_name = short_path.split('.')[0]
            module_name = CLASS_TO_MODULE[class_name]
            # Create full official path: Ball.vel → itasca.ball.Ball.vel
            full_path = f"itasca.{module_name}.{short_path}"
            quick_ref[full_path] = file_ref

        # Remove original short path entries
        for api_name in entries_to_remove:
            del quick_ref[api_name]

        return index

    @staticmethod
    def _load_module_doc(api_name: str, index: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Load module-level documentation.

        Args:
            api_name: API name that might be a module (e.g., "itasca.ball", "itasca.clump")
            index: Loaded index dictionary

        Returns:
            Module documentation dict or None if not a module

        Example:
            Input: "itasca.ball"
            Output: {
                "type": "module",
                "signature": "itasca.ball (module - 9 functions available)",
                "description": "Ball object management...",
                "available_functions": ["itasca.ball.create", ...]
            }
        """
        modules = index.get("modules", {})

        # Extract module name from API name
        # "itasca.ball" -> "ball"
        # "itasca.clump.template" -> "clump.template"
        if not api_name.startswith("itasca."):
            return None

        module_name = api_name.replace("itasca.", "", 1)

        # Check if this module exists
        if module_name not in modules:
            return None

        module_info = modules[module_name]

        # Build list of available functions with full paths
        functions = module_info.get("functions", [])
        available_functions = [f"itasca.{module_name}.{func}" for func in functions]

        func_count = len(functions)

        return {
            "type": "module",
            "signature": f"{api_name} (module - {func_count} function{'s' if func_count != 1 else ''} available)",
            "description": module_info.get("description", f"{module_name} module"),
            "available_functions": available_functions,
            "usage_note": (
                f"Query specific functions (e.g., '{available_functions[0] if available_functions else 'function_name'}') "
                "for detailed documentation including parameters, return types, and examples."
            )
        }

    @staticmethod
    def _expand_contact_keywords(all_keywords: defaultdict) -> defaultdict:
        """Expand itasca.contact.Contact.* entries in keywords to all Contact type variants.

        This ensures keywords.json entries like "itasca.contact.Contact.gap" are
        expanded to all specific Contact types, matching the behavior of index expansion.

        Args:
            all_keywords: Dictionary mapping keywords to API lists

        Returns:
            Modified dictionary with expanded Contact entries

        Example:
            Input:
                {"contact gap": ["itasca.contact.Contact.gap"]}

            Output:
                {"contact gap": [
                    "itasca.BallBallContact.gap",
                    "itasca.BallFacetContact.gap",
                    "itasca.BallPebbleContact.gap",
                    "itasca.PebblePebbleContact.gap",
                    "itasca.PebbleFacetContact.gap"
                ]}
        """
        from pfc_mcp.docs.python_api.types.contact import CONTACT_TYPES

        # Create a new dict to store expanded results
        expanded_keywords = defaultdict(list)

        for keyword, api_list in all_keywords.items():
            expanded_apis = []

            for api_name in api_list:
                # Check if this is a Contact abstract path
                if api_name.startswith("itasca.contact.Contact."):
                    # Extract method name after "itasca.contact.Contact."
                    method_name = api_name.split(".", 3)[3]

                    # Expand to all Contact types
                    for contact_type in CONTACT_TYPES:
                        expanded_apis.append(f"itasca.{contact_type}.{method_name}")
                else:
                    # Keep non-Contact APIs as-is
                    expanded_apis.append(api_name)

            expanded_keywords[keyword] = expanded_apis

        return expanded_keywords

    @staticmethod
    def _merge_keywords(target: defaultdict, source: Dict[str, list]) -> None:
        """Merge keywords from source into target without overwriting.

        When a keyword exists in both target and source, their API lists
        are merged (deduplicated).

        Args:
            target: Target defaultdict to merge into
            source: Source dict to merge from
        """
        for keyword, apis in source.items():
            # Skip comment entries
            if keyword.startswith("_comment"):
                continue

            # Extend the list (merge, don't replace)
            target[keyword].extend(apis)

            # Deduplicate while preserving order
            target[keyword] = list(dict.fromkeys(target[keyword]))

    @staticmethod
    def _load_keywords_recursive(directory: Path, all_keywords: defaultdict) -> None:
        """Recursively load keywords from a directory tree.

        Scans the given directory and all subdirectories for keywords.json files
        and merges them into all_keywords.

        Args:
            directory: Directory to scan
            all_keywords: Target defaultdict to accumulate keywords
        """
        for item in directory.iterdir():
            if item.is_dir():
                # Load keywords.json in this directory if it exists
                keywords_file = item / "keywords.json"
                if keywords_file.exists():
                    with open(keywords_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        DocumentationLoader._merge_keywords(
                            all_keywords,
                            data.get("keywords", {})
                        )

                # Recursively process subdirectories
                DocumentationLoader._load_keywords_recursive(item, all_keywords)

    @staticmethod
    def load_module(module_key: str) -> Optional[Dict[str, Any]]:
        """Load module documentation by index key.

        Args:
            module_key: Module key from index (e.g., "itasca", "ball", "wall.facet")

        Returns:
            Module documentation dict with:
                - module: Module name
                - description: Module description
                - functions: List of function definitions

            Returns None if module not found.

        Example:
            >>> doc = DocumentationLoader.load_module("ball")
            >>> doc["module"]
            "itasca.ball"
            >>> len(doc["functions"])
            9
        """
        index = DocumentationLoader.load_index()
        modules = index.get("modules", {})

        if module_key not in modules:
            return None

        module_info = modules[module_key]
        file_path = module_info.get("file")

        if not file_path:
            # Return basic info from index if no file specified
            return {
                "module": f"itasca.{module_key}" if module_key != "itasca" else "itasca",
                "description": module_info.get("description", ""),
                "functions": module_info.get("functions", [])
            }

        # Load full module documentation
        doc_path = PFC_DOCS_SOURCE / file_path
        if not doc_path.exists():
            # Return basic info from index
            return {
                "module": f"itasca.{module_key}" if module_key != "itasca" else "itasca",
                "description": module_info.get("description", ""),
                "functions": module_info.get("functions", [])
            }

        with open(doc_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def load_function(module_key: str, func_name: str) -> Optional[Dict[str, Any]]:
        """Load function documentation from a module.

        Args:
            module_key: Module key from index (e.g., "itasca", "ball")
            func_name: Function name (e.g., "create", "cycle")

        Returns:
            Function documentation dict with:
                - name: Function name
                - signature: Function signature
                - description: Detailed description
                - parameters: List of parameter definitions
                - returns: Return value information
                - examples: Usage examples (optional)

            Returns None if function not found.

        Example:
            >>> doc = DocumentationLoader.load_function("ball", "create")
            >>> doc["signature"]
            "itasca.ball.create(radius: float, centroid: vec, id: int = None) -> Ball"
        """
        module_doc = DocumentationLoader.load_module(module_key)
        if not module_doc:
            return None

        functions = module_doc.get("functions", [])
        for func in functions:
            if isinstance(func, dict) and func.get("name") == func_name:
                return func

        return None

    @staticmethod
    def load_object(object_name: str) -> Optional[Dict[str, Any]]:
        """Load object documentation by class name.

        Args:
            object_name: Object class name (e.g., "Ball", "Contact", "Wall")

        Returns:
            Object documentation dict with:
                - class: Class name
                - description: Object description
                - note: Usage note (optional)
                - method_groups: Dict of method group names to method lists
                - methods: List of method definitions (if full doc available)

            Returns None if object not found.

        Example:
            >>> doc = DocumentationLoader.load_object("Ball")
            >>> doc["class"]
            "Ball"
            >>> "position" in doc["method_groups"]
            True
        """
        index = DocumentationLoader.load_index()
        objects = index.get("objects", {})

        if object_name not in objects:
            return None

        object_info = objects[object_name]
        file_path = object_info.get("file")

        if not file_path:
            # Return basic info from index
            return object_info

        # Load full object documentation
        doc_path = PFC_DOCS_SOURCE / file_path
        if not doc_path.exists():
            return object_info

        with open(doc_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def load_method(object_name: str, method_name: str) -> Optional[Dict[str, Any]]:
        """Load method documentation from an object.

        Args:
            object_name: Object class name (e.g., "Ball", "Wall")
            method_name: Method name (e.g., "pos", "vel")

        Returns:
            Method documentation dict with:
                - name: Method name
                - signature: Method signature
                - description: Detailed description
                - parameters: List of parameter definitions (optional)
                - returns: Return value information

            Returns None if method not found.

        Example:
            >>> doc = DocumentationLoader.load_method("Ball", "pos")
            >>> doc["signature"]
            "ball.pos() -> vec"
        """
        object_doc = DocumentationLoader.load_object(object_name)
        if not object_doc:
            return None

        methods = object_doc.get("methods", [])
        for method in methods:
            if isinstance(method, dict) and method.get("name") == method_name:
                return method

        return None

    @staticmethod
    def clear_cache():
        """Clear all cached data.

        Useful for testing or when documentation files are updated.
        """
        DocumentationLoader.load_index.cache_clear()
        DocumentationLoader.load_all_keywords.cache_clear()
