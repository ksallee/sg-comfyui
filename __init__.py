"""ComfyUI entry point.

ComfyUI imports `custom_nodes/<dir>/__init__.py` and reads the mappings from it (nodes.py:2263), so
the mappings must exist at the repo root even though the package lives under src/.
"""

from .src.comfyui_fpt import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .src.comfyui_fpt import routes

# Served at /extensions/comfyui-flow-production-tracking/ (server.py:1244).
WEB_DIRECTORY = "web"

routes.register()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
