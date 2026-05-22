"""Unit tests for the PFC bridge bootstrap script (``addon.py``).

``addon.py`` runs inside PFC's embedded Python (3.6 on PFC 6/7), while this
suite runs on the MCP package's interpreter (3.10+). These tests therefore
guard the *control flow* of the bootstrap -- argument construction, the
index-fallback loop, pip entry-point resolution, and the upgrade prompt --
and deliberately do NOT exercise real pip behaviour or the in-PFC ``start()``
path. Confirming the bootstrap against an actual PFC interpreter stays a
manual step.
"""

import logging
import sys
import types

import pytest

import addon

# --- _build_install_args -------------------------------------------------


def test_build_install_args_core_structure():
    args = addon._build_install_args("https://example.test/simple/", ())

    assert args[0] == "install"
    assert "--user" in args
    assert "-U" in args
    # The package to install is always the final positional argument.
    assert args[-1] == addon.PACKAGE_NAME


def test_build_install_args_index_url_paired_with_value():
    url = "https://example.test/simple/"
    args = addon._build_install_args(url, ())

    assert args[args.index("--index-url") + 1] == url


def test_build_install_args_one_trusted_host_flag_per_host():
    hosts = ("a.example", "b.example", "c.example")
    args = addon._build_install_args("https://example.test/simple/", hosts)

    assert args.count("--trusted-host") == len(hosts)
    for host in hosts:
        # Every host value is introduced by its own --trusted-host flag.
        assert args[args.index(host) - 1] == "--trusted-host"


def test_build_install_args_no_trusted_host_when_empty():
    args = addon._build_install_args("https://example.test/simple/", ())

    assert "--trusted-host" not in args


def test_build_install_args_progress_flags_track_python_version():
    # The quiet-output flags are gated on the *runner* interpreter; pin that
    # documented behaviour rather than a fixed expectation.
    args = addon._build_install_args("https://example.test/simple/", ())
    flags_present = "--no-warn-script-location" in args

    assert flags_present is (sys.version_info >= (3, 10))


# --- _resolve_pip_main ---------------------------------------------------


def test_resolve_pip_main_prefers_modern_entry_point(monkeypatch):
    # _resolve_pip_main returns the entry point opaquely, so a marker value
    # under the `.main` attribute is enough to assert which probe won.
    cli_mod = types.ModuleType("pip._internal.cli.main")
    cli_mod.main = "modern-entry-point"
    internal_mod = types.ModuleType("pip._internal")
    internal_mod.main = "legacy-internal-entry-point"
    monkeypatch.setitem(sys.modules, "pip._internal.cli.main", cli_mod)
    monkeypatch.setitem(sys.modules, "pip._internal", internal_mod)

    # Even with the older entry point also importable, the modern one wins.
    assert addon._resolve_pip_main() == "modern-entry-point"


def test_resolve_pip_main_returns_none_when_pip_absent(monkeypatch):
    # Force every probed import to fail: a None entry in sys.modules makes
    # `import pip` raise, and clearing the submodule cache stops an already
    # imported `pip._internal.*` from satisfying the import behind pip's back.
    monkeypatch.setitem(sys.modules, "pip", None)
    for name in ("pip._internal", "pip._internal.cli", "pip._internal.cli.main"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    assert addon._resolve_pip_main() is None


# --- _run_pip ------------------------------------------------------------


def test_run_pip_passes_args_and_returns_code(monkeypatch):
    received = []

    def fake_pip_main(args):
        received.append(args)
        return 0

    monkeypatch.setattr(addon, "_resolve_pip_main", lambda: fake_pip_main)

    assert addon._run_pip(["install", "pkg"]) == 0
    assert received == [["install", "pkg"]]


def test_run_pip_raises_helpful_error_when_no_pip(monkeypatch):
    monkeypatch.setattr(addon, "_resolve_pip_main", lambda: None)

    with pytest.raises(RuntimeError, match="Could not locate pip"):
        addon._run_pip(["install", "pkg"])


def test_run_pip_restores_logging_raise_exceptions(monkeypatch):
    monkeypatch.setattr(addon, "_resolve_pip_main", lambda: lambda _args: 0)
    monkeypatch.setattr(logging, "raiseExceptions", True)

    addon._run_pip(["install", "pkg"])

    assert logging.raiseExceptions is True


def test_run_pip_restores_logging_even_on_failure(monkeypatch):
    def boom(_args):
        raise RuntimeError("pip blew up")

    monkeypatch.setattr(addon, "_resolve_pip_main", lambda: boom)
    monkeypatch.setattr(logging, "raiseExceptions", True)

    with pytest.raises(RuntimeError, match="blew up"):
        addon._run_pip(["install", "pkg"])

    assert logging.raiseExceptions is True


# --- _install_bridge -----------------------------------------------------


@pytest.fixture
def clean_pip_env(monkeypatch):
    """Neutralize the env vars `_install_bridge` reads and writes."""
    monkeypatch.delenv("PFC_MCP_PIP_INDEX_URL", raising=False)
    monkeypatch.delenv("PIP_DISABLE_PIP_VERSION_CHECK", raising=False)


def _stub_run_pip(monkeypatch, codes):
    """Stub `_run_pip` to yield `codes` in order; return the call log."""
    calls = []
    code_iter = iter(codes)

    def fake_run_pip(args):
        calls.append(args)
        return next(code_iter)

    monkeypatch.setattr(addon, "_run_pip", fake_run_pip)
    return calls


def test_install_bridge_returns_zero_on_first_index(monkeypatch, clean_pip_env):
    calls = _stub_run_pip(monkeypatch, [0])

    assert addon._install_bridge() == 0
    # Success on the primary index must not fall through to the mirror.
    assert len(calls) == 1


def test_install_bridge_falls_back_to_mirror(monkeypatch, clean_pip_env):
    calls = _stub_run_pip(monkeypatch, [2, 0])

    assert addon._install_bridge() == 0
    assert len(calls) == 2
    # The retry targets a different index than the failed first attempt.
    first_url = calls[0][calls[0].index("--index-url") + 1]
    second_url = calls[1][calls[1].index("--index-url") + 1]
    assert first_url != second_url


def test_install_bridge_returns_last_code_when_all_fail(monkeypatch, clean_pip_env):
    calls = _stub_run_pip(monkeypatch, [2, 3])

    assert addon._install_bridge() == 3
    assert len(calls) == len(addon.DEFAULT_INDEXES)


def test_install_bridge_honors_index_override(monkeypatch, clean_pip_env):
    monkeypatch.setenv("PFC_MCP_PIP_INDEX_URL", "https://override.test/simple/")
    calls = _stub_run_pip(monkeypatch, [0])

    assert addon._install_bridge() == 0
    # An explicit override collapses to a single index, no mirror fallback.
    assert len(calls) == 1
    assert "https://override.test/simple/" in calls[0]


# --- _prompt_for_upgrade -------------------------------------------------


def test_prompt_for_upgrade_true_when_not_installed():
    # No installed version -> fresh install, no prompt shown.
    assert addon._prompt_for_upgrade(None) is True


@pytest.mark.parametrize("answer", ["y", "Y", "yes", "YES", "  yes  "])
def test_prompt_for_upgrade_accepts_affirmative(monkeypatch, answer):
    monkeypatch.setattr("builtins.input", lambda _prompt="": answer)

    assert addon._prompt_for_upgrade("0.1.0") is True


@pytest.mark.parametrize("answer", ["n", "no", "", "  ", "maybe"])
def test_prompt_for_upgrade_rejects_non_affirmative(monkeypatch, answer):
    monkeypatch.setattr("builtins.input", lambda _prompt="": answer)

    assert addon._prompt_for_upgrade("0.1.0") is False


def test_prompt_for_upgrade_false_when_input_unavailable(monkeypatch):
    def no_input(_prompt=""):
        raise EOFError("no stdin in this host")

    monkeypatch.setattr("builtins.input", no_input)

    assert addon._prompt_for_upgrade("0.1.0") is False


# --- DEFAULT_INDEXES config ----------------------------------------------


def test_default_indexes_are_well_formed():
    assert addon.DEFAULT_INDEXES  # non-empty
    for index_url, trusted_hosts in addon.DEFAULT_INDEXES:
        assert index_url.startswith("https://")
        assert isinstance(trusted_hosts, tuple)
