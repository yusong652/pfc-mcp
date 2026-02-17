"""PFC Documentation path configuration.

Defines paths for static documentation resources bundled with pfc-mcp.
All paths are resolved relative to this package's resources/ directory.
"""

from pathlib import Path

# Base path for all documentation resources
_RESOURCES_DIR = Path(__file__).parent / "resources"

# Static source documentation (version-controlled, JSON format)
# Contains PFC Python SDK API documentation exported from official docs
PFC_DOCS_SOURCE = _RESOURCES_DIR / "python_sdk_docs"

# Command documentation root (version-controlled, JSON format)
# Contains PFC command documentation with 115 commands across 7 categories
PFC_COMMAND_DOCS_ROOT = _RESOURCES_DIR / "command_docs"

# Reference documentation (version-controlled, JSON format)
# Syntax elements used within commands: contact models, range elements, etc.
PFC_REFERENCES_ROOT = _RESOURCES_DIR / "references"

# Contact models subdirectory (within references)
PFC_CONTACT_MODELS_ROOT = PFC_REFERENCES_ROOT / "contact-models"

# Maximum number of API matches to return from keyword search
SDK_SEARCH_TOP_N = 3
