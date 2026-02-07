# PFC Command Documentation Structure Design

## Overview
This document describes the structure and format of PFC command documentation, designed to complement the existing Python SDK documentation system.

## Design Principles

1. **Consistency with Python SDK**: Mirror the structure of `python_sdk_docs` for unified search and retrieval
2. **Command Hierarchy**: Reflect PFC's command hierarchy (e.g., `ball generate`, `contact model linear`)
3. **Searchability**: Support both exact command matching and keyword-based fuzzy search
4. **Completeness**: Include syntax, parameters, examples, and relationships to Python SDK

## Directory Structure

```
command_docs/
├── index.json                          # Master index (similar to python_sdk_docs/index.json)
├── commands/                           # Command documentation root
│   ├── ball/                           # Ball object commands
│   ├── wall/                           # Wall object commands
│   ├── clump/                          # Clump object commands
│   ├── contact/                        # Contact commands
│   │   └── model/                      # Contact model subcommands
│   ├── model/                          # Model system commands
│   ├── measure/                        # Measure utility commands
│   └── set/                            # Set system settings
```

## File Format Specifications

### 1. index.json (Master Index)

```json
{
  "version": "1.0",
  "description": "PFC command documentation index for quick lookup",
  "categories": {
    "ball": {
      "description": "Ball object creation and manipulation commands",
      "file": "commands/ball/category.json",
      "commands": ["generate", "delete", "attribute", "property", "group"]
    },
    "wall": {
      "description": "Wall object creation and manipulation commands",
      "file": "commands/wall/category.json",
      "commands": ["create", "generate", "delete", "attribute"]
    },
    "contact": {
      "description": "Contact and contact model commands",
      "file": "commands/contact/category.json",
      "subcategories": ["model"],
      "commands": ["property", "group"]
    },
    "model": {
      "description": "Model system control commands",
      "file": "commands/model/category.json",
      "commands": ["solve", "cycle", "configure", "domain"]
    }
  },
  "quick_ref": {
    "ball generate": "commands/ball/generate.json",
    "ball delete": "commands/ball/delete.json",
    "contact model linear": "commands/contact/model/linear.json",
    "model solve": "commands/model/solve.json"
  },
  "python_sdk_alternatives": {
    "ball generate cubic": {
      "reason": "Python SDK doesn't support packing patterns",
      "python_alternative": "itasca.ball.create() with manual positioning",
      "recommendation": "Use command for batch generation with patterns"
    }
  }
}
```

### 2. category.json (Category Metadata)

Located in each command category directory (e.g., `commands/ball/category.json`):

```json
{
  "category": "ball",
  "full_name": "Ball Commands",
  "description": "Commands for creating, modifying, and managing ball objects in PFC",
  "command_prefix": "ball",
  "python_module": "itasca.ball",
  "commands": [
    {
      "name": "generate",
      "file": "generate.json",
      "short_description": "Generate balls with various packing patterns",
      "python_available": false
    },
    {
      "name": "delete",
      "file": "delete.json",
      "short_description": "Delete balls based on range or group",
      "python_available": "partial"
    },
    {
      "name": "attribute",
      "file": "attribute.json",
      "short_description": "Set ball attributes",
      "python_available": true,
      "python_alternative": "Ball.set_* methods"
    }
  ]
}
```

### 3. Command Documentation File Format

Each command file (e.g., `commands/ball/generate.json`):

```json
{
  "command": "ball generate",
  "category": "ball",
  "subcategory": null,
  "description": "Generate balls with specified packing patterns and distributions",
  "syntax": "ball generate <keyword> <range> [keyword <value>]...",

  "keywords": [
    {
      "name": "cubic",
      "type": "packing_pattern",
      "description": "Generate balls in cubic packing pattern",
      "required_keywords": ["box"],
      "optional_keywords": ["radius", "porosity", "group"]
    },
    {
      "name": "hexagonal",
      "type": "packing_pattern",
      "description": "Generate balls in hexagonal close packing",
      "required_keywords": ["box"],
      "optional_keywords": ["radius", "porosity", "group"]
    },
    {
      "name": "box",
      "type": "range",
      "description": "Bounding box for ball generation",
      "syntax": "box <x1 y1 z1> <x2 y2 z2>"
    },
    {
      "name": "radius",
      "type": "property",
      "description": "Ball radius or radius range",
      "syntax": "radius <rmin> [rmax]",
      "default": "Auto-calculated from porosity"
    }
  ],

  "examples": [
    {
      "command": "ball generate cubic box -5 -5 -5 5 5 5 radius 0.5",
      "description": "Generate balls in cubic packing within a 10x10x10 box with radius 0.5"
    },
    {
      "command": "ball generate hexagonal box 0 0 0 10 10 10 radius 0.3 0.5 group ballGroup",
      "description": "Generate balls in hexagonal packing with radius between 0.3 and 0.5"
    }
  ],

  "python_sdk_alternative": {
    "available": false,
    "reason": "Python SDK doesn't support packing patterns for batch creation",
    "workaround": "Use itasca.ball.create() in a loop with manual positioning",
    "recommendation": "Prefer this command for batch generation with patterns"
  },

  "related_commands": [
    "ball delete",
    "ball attribute",
    "model cycle"
  ],

  "related_python_apis": [
    "itasca.ball.create()",
    "itasca.ball.count()"
  ],

  "notes": [
    "Generated balls inherit properties from the default contact model",
    "Use 'model cycle' after generation to allow balls to settle",
    "Large numbers of balls may require significant memory"
  ],

  "documentation_url": "https://docs.itascacg.com/pfc700/pfc/docproject/source/manual/ball/commands/cmd_ball.generate.html"
}
```

### 4. keywords.json (Search Keywords)

Located in each category directory for fuzzy search support:

```json
{
  "category": "ball",
  "keywords": {
    "generate": ["create", "make", "add", "cubic", "hexagonal", "packing", "batch"],
    "delete": ["remove", "erase", "clear"],
    "attribute": ["property", "set", "modify", "change", "density", "radius"],
    "group": ["assign", "organize", "slot"]
  },
  "command_patterns": {
    "ball generate": ["ball create multiple", "generate balls", "create balls", "ball packing"],
    "ball delete": ["remove balls", "delete balls", "ball remove"],
    "ball attribute": ["set ball property", "modify ball", "ball density", "ball radius"]
  }
}
```

## Search Strategy

### 1. Exact Command Match
- Input: `ball generate cubic`
- Match: `commands/ball/generate.json` → filter by `cubic` keyword

### 2. Partial Command Match
- Input: `generate cubic`
- Match: Search all `generate.json` files across categories

### 3. Keyword-Based Search
- Input: `create balls with packing`
- Match: Use `keywords.json` to find relevant commands
- Score based on keyword matches

### 4. Natural Language Query
- Input: `how to make balls in a cubic pattern`
- Match: Semantic search across descriptions and keywords
- Return top N matches with context

## Integration with Python SDK Docs

### Cross-Reference Fields

Each command doc includes:
- `python_sdk_alternative`: Whether Python SDK can achieve the same result
- `related_python_apis`: List of related Python API paths
- Recommendation on when to use command vs Python SDK

Each Python SDK doc includes:
- `limitations`: What the API cannot do
- `fallback_commands`: Suggested commands for unsupported operations

## Scoring System (for Search)

Similar to `pfc_query_python_api.py`:

```python
# Score ranges:
#   950-999: Exact command match
#   800-949: Exact keyword match
#   700-799: Partial keyword match
#   400-699: Semantic/fuzzy match
#   0-399:   Low relevance (filtered out)

HIGH_CONFIDENCE_THRESHOLD = 700
```

## Example Usage in pfc_query_command Tool

```python
# User query: "generate balls cubic"
# 1. Load index.json
# 2. Check quick_ref for exact match: "ball generate cubic" → not found
# 3. Check quick_ref for partial match: "ball generate" → commands/ball/generate.json
# 4. Load commands/ball/generate.json
# 5. Filter keywords containing "cubic"
# 6. Return full documentation with "cubic" packing pattern highlighted
```

## Migration Path

1. **Phase 1**: Create index.json and category.json files for main categories
2. **Phase 2**: Document high-priority commands (ball, wall, contact model, model solve)
3. **Phase 3**: Add keywords.json for each category
4. **Phase 4**: Complete documentation for all remaining commands
5. **Phase 5**: Add cross-references with Python SDK docs

## File Naming Conventions

- Category directories: lowercase (e.g., `ball/`, `contact/`)
- Command files: lowercase with underscores if needed (e.g., `generate.json`, `model_solve.json`)
- Special characters in commands: use underscores (e.g., `contact model linear` → `model/linear.json`)

## Validation Schema

Each JSON file should be validated against a JSON schema to ensure consistency:
- Required fields must be present
- Types must match specification
- Cross-references must be valid file paths

---

**Design Version**: 1.0
**Created**: 2025-01-21
**Purpose**: Foundation for `pfc_query_command` tool implementation
