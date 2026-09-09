"""ComfyUI entry point.

ComfyUI imports `custom_nodes/<dir>/__init__.py` and reads the mappings from it (nodes.py:2263), so
they must exist at the repo root even though the package lives under `src/`.

The classes come from `comfyui_sg.nodes` rather than from the package `__init__`, which stays free
of them: importing `comfyui_sg` must not pull in torch, or the setup commands cannot run on a plain
Python.
"""
from .src.comfyui_sg import routes
from .src.comfyui_sg.nodes import SGLoadVersion, SGPublishVersion

# Keys are written into every saved workflow, so they are permanent.
NODE_CLASS_MAPPINGS = {"SGLoadVersion": SGLoadVersion,
                       "SGPublishVersion": SGPublishVersion}
NODE_DISPLAY_NAME_MAPPINGS = {"SGLoadVersion": "SG Load",
                              "SGPublishVersion": "SG Publish"}

# Served at /extensions/sg-comfyui/ (server.py:1244).
WEB_DIRECTORY = "web"

routes.register()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
