"""Allow running as: python -m pfc_mcp_bridge"""

import argparse

from pfc_mcp_bridge import __version__, start


def main():
    parser = argparse.ArgumentParser(
        prog="pfc-mcp-bridge",
        description="PFC Bridge - WebSocket bridge for ITASCA PFC",
    )
    parser.add_argument(
        "--version", "-v", action="version", version="pfc-mcp-bridge {}".format(__version__)
    )
    parser.add_argument("--host", default="localhost", help="server host (default: localhost)")
    parser.add_argument("--port", type=int, default=9001, help="server port (default: 9001)")
    parser.add_argument("--mode", choices=["auto", "gui", "console"], default="auto",
                        help="task pump mode (default: auto)")
    args = parser.parse_args()

    start(host=args.host, port=args.port, mode=args.mode)


main()
