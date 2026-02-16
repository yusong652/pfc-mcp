"""Tests for command_splitter: multi-line itasca.command() splitting."""

import sys
import os
import textwrap

import pytest

# Add bridge source to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pfc-bridge", "src"))

from pfc_mcp_bridge.utils.command_splitter import split_pfc_commands, preprocess_script


# ── split_pfc_commands tests ────────────────────────────────────────


class TestSplitPfcCommands:
    """Tests for splitting a multi-line PFC command string."""

    def test_basic_split(self):
        text = "model new\nmodel solve"
        assert split_pfc_commands(text) == ["model new", "model solve"]

    def test_multiple_commands(self):
        text = "model new\nmodel domain extent -5 5\nball generate number 50\nmodel solve"
        result = split_pfc_commands(text)
        assert len(result) == 4
        assert result[0] == "model new"
        assert result[3] == "model solve"

    def test_empty_lines_stripped(self):
        text = "\nmodel new\n\n\nmodel solve\n"
        assert split_pfc_commands(text) == ["model new", "model solve"]

    def test_whitespace_stripped(self):
        text = "  model new  \n    model solve ratio 1e-5  "
        assert split_pfc_commands(text) == ["model new", "model solve ratio 1e-5"]

    def test_comment_lines_skipped(self):
        text = "; setup\nmodel new\n; now solve\nmodel solve"
        assert split_pfc_commands(text) == ["model new", "model solve"]

    def test_line_continuation(self):
        text = "ball generate ...\n  radius 0.2 0.3 ...\n  box -1 1\nmodel solve"
        result = split_pfc_commands(text)
        assert len(result) == 2
        assert result[0] == "ball generate radius 0.2 0.3 box -1 1"
        assert result[1] == "model solve"

    def test_continuation_at_end(self):
        """Continuation at end of input should still produce a command."""
        text = "ball generate ...\n  radius 0.2"
        result = split_pfc_commands(text)
        assert result == ["ball generate radius 0.2"]

    def test_single_command(self):
        text = "model solve ratio 1e-5"
        assert split_pfc_commands(text) == ["model solve ratio 1e-5"]

    def test_empty_string(self):
        assert split_pfc_commands("") == []

    def test_only_whitespace(self):
        assert split_pfc_commands("  \n  \n  ") == []

    def test_only_comments(self):
        assert split_pfc_commands("; comment 1\n; comment 2") == []


# ── preprocess_script tests ─────────────────────────────────────────


class TestPreprocessScript:
    """Tests for full script preprocessing."""

    def test_multiline_itasca_command(self):
        script = textwrap.dedent('''\
            import itasca
            itasca.command("""
            model new
            model solve
            """)
            print("done")
        ''')
        result = preprocess_script(script)
        assert 'itasca.command("model new")' in result
        assert 'itasca.command("model solve")' in result
        assert '"""' not in result or result.count('"""') == 0
        assert 'print("done")' in result

    def test_multiline_command_import(self):
        """from itasca import command style."""
        script = textwrap.dedent('''\
            from itasca import command
            command("""
            model new
            model solve
            """)
        ''')
        result = preprocess_script(script)
        assert 'command("model new")' in result
        assert 'command("model solve")' in result

    def test_single_line_command_unchanged(self):
        script = 'itasca.command("model new")\n'
        assert preprocess_script(script) == script

    def test_variable_arg_unchanged(self):
        script = textwrap.dedent('''\
            cmd = "model new"
            itasca.command(cmd)
        ''')
        assert preprocess_script(script) == script

    def test_preserves_indentation(self):
        script = textwrap.dedent('''\
            def run():
                itasca.command("""
                model new
                model solve
                """)
        ''')
        result = preprocess_script(script)
        # Each replacement line should have the same indent as the original call
        for line in result.split("\n"):
            if 'itasca.command("model' in line:
                assert line.startswith("    "), "Expected 4-space indent, got: " + repr(line)

    def test_preserves_surrounding_code(self):
        script = textwrap.dedent('''\
            import itasca
            x = 1
            itasca.command("""
            model new
            model solve
            """)
            y = 2
        ''')
        result = preprocess_script(script)
        assert "import itasca" in result
        assert "x = 1" in result
        assert "y = 2" in result

    def test_multiple_multiline_calls(self):
        script = textwrap.dedent('''\
            itasca.command("""
            model new
            model domain extent -5 5
            """)
            print("setup done")
            itasca.command("""
            model cycle 1000
            model solve
            """)
        ''')
        result = preprocess_script(script)
        assert 'itasca.command("model new")' in result
        assert 'itasca.command("model domain extent -5 5")' in result
        assert 'print("setup done")' in result
        assert 'itasca.command("model cycle 1000")' in result
        assert 'itasca.command("model solve")' in result

    def test_continuation_in_command(self):
        script = textwrap.dedent('''\
            itasca.command("""
            ball generate ...
              radius 0.2
            model solve
            """)
        ''')
        result = preprocess_script(script)
        assert 'itasca.command("ball generate radius 0.2")' in result
        assert 'itasca.command("model solve")' in result

    def test_syntax_error_returns_original(self):
        """Malformed Python should be returned unchanged."""
        script = "def broken(\n"
        assert preprocess_script(script) == script

    def test_no_commands_returns_original(self):
        script = "x = 1\ny = 2\n"
        assert preprocess_script(script) == script

    def test_single_command_in_multiline_string_unchanged(self):
        """Multi-line string with only one actual command → no split needed."""
        script = textwrap.dedent('''\
            itasca.command("""
            model new
            """)
        ''')
        result = preprocess_script(script)
        # Should be unchanged since there's only 1 command
        assert result == script

    def test_real_drop_particles_script(self):
        """Simulate the actual drop_particles.py that caused the blocking."""
        script = textwrap.dedent('''\
            import itasca
            from itasca import ball, wall, command

            def run():
                command("""
                model new
                model large-strain on
                model domain extent -5 5
                wall generate box -2 2
                contact cmat default model linear property kn 1e6 ks 1e6 fric 0.3
                ball generate number 50 radius 0.2 0.3 box -1.5 1.5 -1.5 1.5 -1.5 1.5
                ball attribute density 2500
                model gravity 0 0 -9.81
                model cycle 1000
                model solve
                """)
                print("Particles dropped into box.")

            if __name__ == "__main__":
                run()
        ''')
        result = preprocess_script(script)
        # All commands should be split
        assert 'command("model new")' in result
        assert 'command("model large-strain on")' in result
        assert 'command("model solve")' in result
        # The triple-quoted multi-line string should be gone
        assert '"""' not in result
        # Surrounding code preserved
        assert "def run():" in result
        assert 'print("Particles dropped into box.")' in result
        assert '__name__ == "__main__"' in result
