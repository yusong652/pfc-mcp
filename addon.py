# -*- coding: utf-8 -*-
"""
PFC Bridge bootstrap script.

Use it inside PFC in either of these ways:
1. Copy the file contents into the PFC IPython console and run them
2. Or save/download this file and execute it in PFC GUI

What it does:
1. Detects the currently installed `itasca-mcp-bridge`, if any
2. Lets the user decide whether to upgrade to the latest published version
3. Installs `itasca-mcp-bridge` automatically when it is not installed yet
4. Ensures the user site-packages directory is importable
5. Imports `itasca_mcp_bridge` and `websockets`
6. Starts the bridge
"""

import importlib
import logging
import os
import sys


PACKAGE_NAME = "itasca-mcp-bridge"
PORT = 9001  # Change this to run multiple bridges on different ports

# Index URLs tried in order. Mirrors act as a fallback when the primary
# is unreachable (corporate proxies, slow international routes).
DEFAULT_INDEXES = [
    ("https://pypi.org/simple/", ("pypi.org", "files.pythonhosted.org")),
    ("https://pypi.tuna.tsinghua.edu.cn/simple/", ("pypi.tuna.tsinghua.edu.cn",)),
]


def _ensure_user_site_on_path():
    try:
        import site

        user_site = site.getusersitepackages()
    except Exception:
        return

    if isinstance(user_site, str) and user_site and user_site not in sys.path:
        sys.path.append(user_site)


def _build_install_args(index_url, trusted_hosts):
    args = [
        "install",
        "--user",
        "-U",
        "--disable-pip-version-check",
        "--default-timeout", "120",
        "--retries", "5",
        "--index-url", index_url,
    ]
    for host in trusted_hosts:
        args += ["--trusted-host", host]
    if sys.version_info >= (3, 10):
        args += ["--no-warn-script-location", "--progress-bar", "off"]
    args.append(PACKAGE_NAME)
    return args


def _resolve_pip_main():
    """Locate pip's callable entry point.

    There is no single stable location. `pip.main` exists in pip <= 9
    (what PFC 6.0 ships), was removed in pip 10.0, and was later restored
    as an internal-only shim; `pip._internal.main` covers pip 10 .. 19.2;
    `pip._internal.cli.main.main` covers pip >= 19.3. The embedded PFC
    Python may carry any pip version, so probe each location in turn
    rather than guessing from the pip or Python version.
    """
    try:
        from pip._internal.cli.main import main as pip_main  # pip >= 19.3

        return pip_main
    except Exception:
        pass
    try:
        from pip._internal import main as pip_main  # pip 10 .. 19.2

        return pip_main
    except Exception:
        pass
    try:
        from pip import main as pip_main  # pip <= 9 (PFC 6.0)

        return pip_main
    except Exception:
        pass
    return None


def _run_pip(args):
    pip_main = _resolve_pip_main()
    if pip_main is None:
        raise RuntimeError(
            "Could not locate pip's Python entry point in this PFC interpreter. "
            "Install the bridge manually, then re-run this script:\n"
            "    python -m pip install --user itasca-mcp-bridge"
        )

    # PFC runs pip inside an IPython host; temporarily suppress logging
    # handler tracebacks that don't reflect actual installation failures.
    previous_raise_exceptions = logging.raiseExceptions
    logging.raiseExceptions = False
    try:
        return pip_main(list(args))
    finally:
        logging.raiseExceptions = previous_raise_exceptions


def _install_bridge():
    os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    override = os.environ.get("PFC_MCP_PIP_INDEX_URL")
    if override:
        indexes = [(override, ())]
    else:
        indexes = DEFAULT_INDEXES

    last_code = 1
    for attempt, (index_url, trusted_hosts) in enumerate(indexes, start=1):
        if attempt > 1:
            print("Primary index failed, retrying with mirror: {}".format(index_url))
        last_code = _run_pip(_build_install_args(index_url, trusted_hosts))
        if last_code == 0:
            return 0
    return last_code


def _load_installed_bridge():
    _ensure_user_site_on_path()
    importlib.invalidate_caches()

    if "itasca_mcp_bridge" in sys.modules:
        del sys.modules["itasca_mcp_bridge"]

    try:
        import itasca_mcp_bridge
    except Exception:
        return None

    return itasca_mcp_bridge


def _import_bridge():
    _ensure_user_site_on_path()
    importlib.invalidate_caches()

    for module_name in ("itasca_mcp_bridge", "websockets"):
        if module_name in sys.modules:
            del sys.modules[module_name]

    import itasca_mcp_bridge
    import websockets

    return itasca_mcp_bridge, websockets


def _prompt_for_upgrade(current_version):
    if current_version is None:
        print("{} is not installed. Installing the latest version ...".format(PACKAGE_NAME))
        return True

    print("Installed itasca-mcp-bridge:", current_version)

    try:
        answer = input("Update to the latest version before start? [y/N]: ")
    except Exception:
        print("Input unavailable. Keeping the current installation.")
        return False

    return answer.strip().lower() in ("y", "yes")


def main():
    print("=" * 60)
    print("PFC MCP Bridge Bootstrap")
    print("=" * 60)
    print("Python:", sys.version.split()[0])

    installed_bridge = _load_installed_bridge()
    installed_version = None
    if installed_bridge is not None:
        installed_version = getattr(installed_bridge, "__version__", "unknown")

    if _prompt_for_upgrade(installed_version):
        code = _install_bridge()
        if code != 0:
            raise RuntimeError(
                "Bridge installation failed (pip exit code {}). The real pip "
                "error is in the output above this message -- read that, not "
                "this line. Common causes: no network route to PyPI, or a "
                "corporate proxy/firewall blocking the index. You can also "
                "install manually and re-run this script:\n"
                "    python -m pip install --user itasca-mcp-bridge".format(code)
            )
    else:
        print("Skipping package upgrade.")

    itasca_mcp_bridge, websockets = _import_bridge()

    print("Using itasca-mcp-bridge:", getattr(itasca_mcp_bridge, "__version__", "unknown"))
    print("Installed websockets:", getattr(websockets, "__version__", "unknown"))
    print("Starting bridge on port {} ...".format(PORT))

    itasca_mcp_bridge.start(port=PORT)


if __name__ == "__main__":
    main()
