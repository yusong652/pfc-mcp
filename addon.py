# -*- coding: utf-8 -*-
"""
PFC Bridge bootstrap script.

Use it inside PFC in either of these ways:
1. Copy the file contents into the PFC IPython console and run them
2. Or save/download this file and execute it in PFC GUI

What it does:
1. Detects the currently installed `pfc-mcp-bridge`, if any
2. Lets the user decide whether to upgrade to the latest published version
3. Installs `pfc-mcp-bridge` automatically when it is not installed yet
4. Ensures the user site-packages directory is importable
5. Imports `pfc_mcp_bridge` and `websockets`
6. Starts the bridge
"""

import importlib
import logging
import os
import sys


PACKAGE_NAME = "pfc-mcp-bridge"
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


def _run_pip(args):
    if sys.version_info < (3, 10):
        import pip

        return pip.main(args)

    from pip._internal.cli.main import main as pip_main

    # PFC 9 runs pip inside an IPython host; temporarily suppress logging
    # handler tracebacks that don't reflect actual installation failures.
    previous_raise_exceptions = logging.raiseExceptions
    logging.raiseExceptions = False
    try:
        return pip_main(args)
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

    if "pfc_mcp_bridge" in sys.modules:
        del sys.modules["pfc_mcp_bridge"]

    try:
        import pfc_mcp_bridge
    except Exception:
        return None

    return pfc_mcp_bridge


def _import_bridge():
    _ensure_user_site_on_path()
    importlib.invalidate_caches()

    for module_name in ("pfc_mcp_bridge", "websockets"):
        if module_name in sys.modules:
            del sys.modules[module_name]

    import pfc_mcp_bridge
    import websockets

    return pfc_mcp_bridge, websockets


def _prompt_for_upgrade(current_version):
    if current_version is None:
        print("{} is not installed. Installing the latest version ...".format(PACKAGE_NAME))
        return True

    print("Installed pfc-mcp-bridge:", current_version)

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
            raise RuntimeError("Bridge installation failed with exit code {}".format(code))
    else:
        print("Skipping package upgrade.")

    pfc_mcp_bridge, websockets = _import_bridge()

    print("Using pfc-mcp-bridge:", getattr(pfc_mcp_bridge, "__version__", "unknown"))
    print("Installed websockets:", getattr(websockets, "__version__", "unknown"))
    print("Starting bridge on port {} ...".format(PORT))

    pfc_mcp_bridge.start(port=PORT)


if __name__ == "__main__":
    main()
