"""The node registry ComfyUI reads. The repo-root `__init__.py` re-exports these two mappings."""
from .nodes import FPTLoadVersion, FPTPublishVersion

# Keys are written into every saved workflow, so they are permanent.
NODE_CLASS_MAPPINGS = {"FPTLoadVersion": FPTLoadVersion,
                       "FPTPublishVersion": FPTPublishVersion}
NODE_DISPLAY_NAME_MAPPINGS = {"FPTLoadVersion": "Flow PT Load Version",
                              "FPTPublishVersion": "Flow PT Publish Version"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
