"""Compatibility wrapper for websocket server module imports.

Supports historical usages such as:

    python -m tiptop.websocket_server

while keeping the canonical implementation in `tiptop.tiptop_websocket_server`.
"""

from .tiptop_websocket_server import TiptopPlanningServer, _run_server, entrypoint

__all__ = ["TiptopPlanningServer", "_run_server", "entrypoint"]


if __name__ == "__main__":
    entrypoint()
