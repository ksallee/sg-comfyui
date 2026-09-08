"""The node registry ComfyUI reads. The repo-root `__init__.py` re-exports these two mappings."""
from .nodes import SGLoadVersion, SGPublishVersion

# Keys are written into every saved workflow, so they are permanent.
NODE_CLASS_MAPPINGS = {"SGLoadVersion": SGLoadVersion,
                       "SGPublishVersion": SGPublishVersion}
NODE_DISPLAY_NAME_MAPPINGS = {"SGLoadVersion": "SG Load",
                              "SGPublishVersion": "SG Publish"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
