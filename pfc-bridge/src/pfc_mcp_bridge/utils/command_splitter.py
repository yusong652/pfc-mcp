"""
Command Splitter - Preprocess scripts to split multi-line itasca.command() calls.

When itasca.command() receives a multi-line string containing multiple PFC
commands, the PFC C extension holds the GIL for the entire batch, blocking
all other Python threads (including the Bridge WebSocket event loop).

This module transforms such calls into individual itasca.command() calls,
allowing the GIL to be released between commands.

Python 3.6 compatible implementation.
"""

import ast
import logging
import re
from typing import List, Optional, Tuple

# Module logger
logger = logging.getLogger("PFC-Server")


def split_pfc_commands(multiline_str):
    # type: (str) -> List[str]
    """Split a multi-line PFC command string into individual commands.

    Handles:
    - Newline-separated commands
    - PFC line continuation with '...' at end of line
    - PFC comments starting with ';'
    - Empty/whitespace-only lines

    Args:
        multiline_str: Multi-line PFC command string

    Returns:
        List of individual PFC command strings
    """
    lines = multiline_str.split("\n")
    commands = []
    current = []  # type: List[str]

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and pure comment lines
        if not stripped or stripped.startswith(";"):
            continue

        # Check for PFC line continuation (... at end)
        if stripped.endswith("..."):
            # Remove the '...' and accumulate
            current.append(stripped[:-3].rstrip())
            continue

        # No continuation — complete the current command
        current.append(stripped)
        joined = " ".join(current)
        if joined.strip():
            commands.append(joined.strip())
        current = []

    # Flush any remaining continuation
    if current:
        joined = " ".join(current)
        if joined.strip():
            commands.append(joined.strip())

    return commands


def _get_string_value(node):
    # type: (ast.AST) -> Optional[str]
    """Extract string value from an AST node (Python 3.6+ compatible).

    Handles both ast.Str (Python 3.6-3.7) and ast.Constant (Python 3.8+).
    """
    # Python 3.6-3.7: ast.Str
    if hasattr(ast, "Str") and isinstance(node, ast.Str):
        return node.s
    # Python 3.8+: ast.Constant
    if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
    return None


def _is_command_call(node):
    # type: (ast.Call) -> bool
    """Check if a Call node is itasca.command() or command()."""
    func = node.func

    # itasca.command(...)
    if isinstance(func, ast.Attribute):
        if (func.attr == "command"
                and isinstance(func.value, ast.Name)
                and func.value.id == "itasca"):
            return True

    # command(...) — from 'from itasca import command'
    if isinstance(func, ast.Name) and func.id == "command":
        return True

    return False


def _find_multiline_command_calls(tree):
    # type: (ast.Module) -> List[Tuple[ast.Call, str]]
    """Find all multi-line itasca.command() calls in the AST.

    Returns:
        List of (call_node, string_value) tuples, sorted by line number descending
        so replacements can be done back-to-front without shifting offsets.
    """
    results = []  # type: List[Tuple[ast.Call, str]]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_command_call(node):
            continue
        # Must have exactly one positional string arg, no kwargs
        if len(node.args) != 1 or node.keywords:
            continue
        value = _get_string_value(node.args[0])
        if value is None:
            continue
        # Only process if it contains multiple PFC commands (newlines)
        if "\n" not in value:
            continue
        # Check it actually has >1 command after splitting
        commands = split_pfc_commands(value)
        if len(commands) <= 1:
            continue
        results.append((node, value))

    # Sort descending by line number (replace back-to-front)
    results.sort(key=lambda pair: pair[0].lineno, reverse=True)
    return results


def _detect_call_name(source_lines, lineno):
    # type: (List[str], int) -> str
    """Detect the command call name used in source (itasca.command or command)."""
    line = source_lines[lineno - 1]  # lineno is 1-based
    if "itasca.command" in line:
        return "itasca.command"
    return "command"


def _find_call_range(source_lines, call_node):
    # type: (List[str], ast.Call) -> Tuple[int, int]
    """Find the line range [start, end) of a call expression in source.

    Tracks parenthesis nesting to find the closing ')'.
    """
    start = call_node.lineno - 1  # 0-based
    depth = 0
    in_string = None  # type: Optional[str]
    escape_next = False

    for i in range(start, len(source_lines)):
        line = source_lines[i]
        for ch in line:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if in_string:
                if ch == in_string:
                    in_string = None
                continue
            if ch in ('"', "'"):
                # Check for triple quotes
                rest = line[line.index(ch):]
                if rest.startswith('"""') or rest.startswith("'''"):
                    in_string = ch  # simplified: track single char
                else:
                    in_string = ch
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return (start, i + 1)  # end is exclusive

    # Fallback: couldn't find closing paren
    return (start, start + 1)


def _build_replacement(call_name, commands, indent):
    # type: (str, List[str], str) -> str
    """Build replacement source lines for split commands.

    Args:
        call_name: 'itasca.command' or 'command'
        commands: List of individual PFC command strings
        indent: Whitespace indentation to preserve

    Returns:
        Replacement source text with one call per line
    """
    lines = []
    for cmd in commands:
        # Escape any single quotes in the command
        escaped = cmd.replace("\\", "\\\\").replace('"', '\\"')
        lines.append('{}{}("{}")'.format(indent, call_name, escaped))
    return "\n".join(lines)


def preprocess_script(script_content):
    # type: (str) -> str
    """Transform multi-line itasca.command() calls into individual calls.

    This is the main entry point. If parsing or transformation fails,
    the original script content is returned unchanged.

    Args:
        script_content: Raw Python script content

    Returns:
        Transformed script content with split command calls
    """
    try:
        tree = ast.parse(script_content)
    except SyntaxError:
        # Can't parse — return as-is (compile() will report the error later)
        return script_content

    calls = _find_multiline_command_calls(tree)
    if not calls:
        return script_content

    source_lines = script_content.split("\n")

    for call_node, cmd_string in calls:
        # Detect indentation and call name from source
        start_line = source_lines[call_node.lineno - 1]
        indent = start_line[: len(start_line) - len(start_line.lstrip())]
        call_name = _detect_call_name(source_lines, call_node.lineno)

        # Find full extent of the call in source
        line_start, line_end = _find_call_range(source_lines, call_node)

        # Split PFC commands and build replacement
        commands = split_pfc_commands(cmd_string)
        replacement = _build_replacement(call_name, commands, indent)

        # Replace the lines
        source_lines[line_start:line_end] = replacement.split("\n")

    result = "\n".join(source_lines)
    logger.debug("Preprocessed script: split %d multi-line command call(s)", len(calls))
    return result
