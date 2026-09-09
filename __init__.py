"""ComfyUI entry point.

ComfyUI imports `custom_nodes/<dir>/__init__.py` and reads the mappings from it (nodes.py:2263), so
they must exist at the repo root even though the package lives under `src/`.
"""
from .src.comfyui_sg import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .src.comfyui_sg import routes

# Served at /extensions/sg-comfyui/ (server.py:1244).
WEB_DIRECTORY = "web"

routes.register()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
